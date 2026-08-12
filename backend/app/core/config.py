from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketplace"

    # Web3 / chain
    WEB3_PROVIDER_URL: str  # e.g. Alchemy/Infura Amoy RPC URL
    CONTRACT_ADDRESS: str
    CONTRACT_ABI_PATH: str = "contracts_abi/ModelRegistry.json"
    CHAIN_ID: int = 80002  # Polygon Amoy

    # Indexer
    INDEXER_START_BLOCK: int = 0        # block the contract was deployed at
    INDEXER_POLL_INTERVAL_SECONDS: float = 4.0
    INDEXER_BLOCK_CHUNK_SIZE: int = 2000  # max block range per get_logs call
    INDEXER_CONFIRMATIONS: int = 5        # reorg safety margin

    # Pinata (used by upload.py in Phase 2, referenced here for completeness)
    PINATA_API_KEY: str = ""
    PINATA_SECRET_API_KEY: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
