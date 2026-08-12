import json
from functools import lru_cache
from pathlib import Path

from web3 import Web3
from web3.contract import Contract

from app.core.config import get_settings


def _load_abi(path: str) -> list:
    abi_path = Path(path)
    if not abi_path.exists():
        raise FileNotFoundError(
            f"ABI not found at {abi_path}. Copy it from "
            f"contracts/artifacts/contracts/ModelRegistry.sol/ModelRegistry.json "
            f"after `npx hardhat compile`."
        )
    with abi_path.open() as f:
        artifact = json.load(f)
    # Hardhat artifacts wrap the ABI in {"abi": [...], "bytecode": ..., ...}
    return artifact["abi"] if "abi" in artifact else artifact


@lru_cache
def get_w3() -> Web3:
    settings = get_settings()
    w3 = Web3(Web3.HTTPProvider(settings.WEB3_PROVIDER_URL))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to {settings.WEB3_PROVIDER_URL}")
    return w3


@lru_cache
def get_contract() -> Contract:
    settings = get_settings()
    w3 = get_w3()
    abi = _load_abi(settings.CONTRACT_ABI_PATH)
    return w3.eth.contract(
        address=Web3.to_checksum_address(settings.CONTRACT_ADDRESS), abi=abi
    )
