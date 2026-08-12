"""
Polling event indexer.

Watches ModelRegistry for ModelRegistered / VersionUpdated / LicensePurchased / Rated
events and mirrors them into Postgres so the API layer never has to touch the chain
for reads. Runs as an asyncio background task started from main.py's lifespan.

NOTE ON EVENT SIGNATURES: adjust the field names below (`modelId`, `ipfsHash`, etc.)
to match whatever you actually named the event args in ModelRegistry.sol. What's
assumed here:

    event ModelRegistered(uint256 indexed modelId, address indexed owner,
                           string ipfsHash, uint256 price, string licenseType);
    event VersionUpdated(uint256 indexed modelId, uint256 versionNumber, string ipfsHash);
    event LicensePurchased(uint256 indexed modelId, address indexed buyer, uint256 price);
    event Rated(uint256 indexed modelId, address indexed rater, uint8 score);
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import Contract

from app.core.config import Settings, get_settings
from app.core.web3_client import get_contract, get_w3
from app.db.models import IndexerState, Model, ModelVersion, Purchase, Rating
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("indexer")

LISTENER_NAME = "model_registry_listener"


class EventListener:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.w3 = get_w3()
        self.contract: Contract = get_contract()
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(self) -> None:
        logger.info("Indexer starting")
        while not self._stop.is_set():
            try:
                await self._poll_once()
            except Exception:
                # Never let a bad RPC response / transient network error kill the loop —
                # log and retry next tick instead of taking the indexer down.
                logger.exception("Indexer poll failed, will retry")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.settings.INDEXER_POLL_INTERVAL_SECONDS
                )
            except asyncio.TimeoutError:
                pass
        logger.info("Indexer stopped")

    async def _poll_once(self) -> None:
        loop = asyncio.get_running_loop()
        chain_head = await loop.run_in_executor(None, lambda: self.w3.eth.block_number)
        # Stay N confirmations behind the tip so a reorg can't leave us with
        # rows for a block that later gets replaced.
        safe_head = chain_head - self.settings.INDEXER_CONFIRMATIONS
        if safe_head < 0:
            return

        async with AsyncSessionLocal() as db:
            from_block = await self._get_checkpoint(db)
            if from_block > safe_head:
                return

            to_block = min(from_block + self.settings.INDEXER_BLOCK_CHUNK_SIZE - 1, safe_head)

            logs = await loop.run_in_executor(None, self._fetch_logs, from_block, to_block)
            for log in logs:
                await self._handle_event(db, log)

            await self._set_checkpoint(db, to_block + 1)
            await db.commit()

            if to_block < safe_head:
                logger.info("Chunk %s-%s indexed, more remaining up to %s", from_block, to_block, safe_head)

    def _fetch_logs(self, from_block: int, to_block: int) -> list:
        """Sync web3 calls — run in executor since web3.py's HTTP provider is blocking."""
        events = [
            self.contract.events.ModelRegistered,
            self.contract.events.VersionUpdated,
            self.contract.events.LicensePurchased,
            self.contract.events.Rated,
        ]
        all_logs = []
        for event in events:
            entries = event.create_filter(fromBlock=from_block, toBlock=to_block).get_all_entries()
            all_logs.extend(entries)
        # Process in the order they actually happened on-chain.
        all_logs.sort(key=lambda e: (e["blockNumber"], e["logIndex"]))
        return all_logs

    async def _handle_event(self, db: AsyncSession, log) -> None:
        name = log["event"]
        args = log["args"]
        handler = {
            "ModelRegistered": self._on_model_registered,
            "VersionUpdated": self._on_version_updated,
            "LicensePurchased": self._on_license_purchased,
            "Rated": self._on_rated,
        }.get(name)
        if handler is None:
            logger.warning("Unhandled event type: %s", name)
            return
        await handler(db, args, log)

    async def _on_model_registered(self, db: AsyncSession, args, log) -> None:
        stmt = (
            pg_insert(Model)
            .values(
                on_chain_id=args["modelId"],
                owner_address=args["owner"],
                latest_ipfs_hash=args["ipfsHash"],
                latest_version=1,
                price_wei=args["price"],
                license_type=args["licenseType"],
                registered_at_block=log["blockNumber"],
            )
            .on_conflict_do_nothing(index_elements=["on_chain_id"])
        )
        await db.execute(stmt)

        model = await self._get_model(db, args["modelId"])
        if model:
            db.add(
                ModelVersion(
                    model_id=model.id,
                    version_number=1,
                    ipfs_hash=args["ipfsHash"],
                    tx_hash=log["transactionHash"].hex(),
                    block_number=log["blockNumber"],
                )
            )

    async def _on_version_updated(self, db: AsyncSession, args, log) -> None:
        model = await self._get_model(db, args["modelId"])
        if not model:
            logger.warning("VersionUpdated for unknown model %s — registration event missed?", args["modelId"])
            return
        model.latest_ipfs_hash = args["ipfsHash"]
        model.latest_version = args["versionNumber"]
        db.add(
            ModelVersion(
                model_id=model.id,
                version_number=args["versionNumber"],
                ipfs_hash=args["ipfsHash"],
                tx_hash=log["transactionHash"].hex(),
                block_number=log["blockNumber"],
            )
        )

    async def _on_license_purchased(self, db: AsyncSession, args, log) -> None:
        model = await self._get_model(db, args["modelId"])
        if not model:
            logger.warning("LicensePurchased for unknown model %s", args["modelId"])
            return
        stmt = (
            pg_insert(Purchase)
            .values(
                model_id=model.id,
                buyer_address=args["buyer"],
                price_paid_wei=args["price"],
                tx_hash=log["transactionHash"].hex(),
                block_number=log["blockNumber"],
            )
            .on_conflict_do_nothing(index_elements=["model_id", "buyer_address"])
        )
        await db.execute(stmt)

    async def _on_rated(self, db: AsyncSession, args, log) -> None:
        model = await self._get_model(db, args["modelId"])
        if not model:
            logger.warning("Rated for unknown model %s", args["modelId"])
            return
        stmt = (
            pg_insert(Rating)
            .values(
                model_id=model.id,
                rater_address=args["rater"],
                score=args["score"],
                tx_hash=log["transactionHash"].hex(),
                block_number=log["blockNumber"],
            )
            .on_conflict_do_update(
                index_elements=["model_id", "rater_address"],
                set_={"score": args["score"], "tx_hash": log["transactionHash"].hex()},
            )
        )
        await db.execute(stmt)

    async def _get_model(self, db: AsyncSession, on_chain_id: int) -> Model | None:
        result = await db.execute(select(Model).where(Model.on_chain_id == on_chain_id))
        return result.scalar_one_or_none()

    async def _get_checkpoint(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(IndexerState).where(IndexerState.listener_name == LISTENER_NAME)
        )
        state = result.scalar_one_or_none()
        if state:
            return state.last_processed_block
        db.add(IndexerState(listener_name=LISTENER_NAME, last_processed_block=self.settings.INDEXER_START_BLOCK))
        await db.commit()
        return self.settings.INDEXER_START_BLOCK

    async def _set_checkpoint(self, db: AsyncSession, block: int) -> None:
        result = await db.execute(
            select(IndexerState).where(IndexerState.listener_name == LISTENER_NAME)
        )
        state = result.scalar_one_or_none()
        if state:
            state.last_processed_block = block
        else:
            db.add(IndexerState(listener_name=LISTENER_NAME, last_processed_block=block))
