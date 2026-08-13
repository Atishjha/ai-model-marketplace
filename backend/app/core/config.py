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

    # Pinata (used by upload.py in Phase 2)
    # PINATA_API_KEY / PINATA_SECRET_API_KEY: legacy key+secret auth, used for
    #   the relay-through-backend upload path (POST /upload).
    # PINATA_JWT: required separately for the v3 files/sign endpoint that
    #   mints direct-to-IPFS signed URLs (POST /upload/signed-url) — Pinata's
    #   newer API only accepts JWT auth, the legacy key+secret doesn't work there.
    PINATA_API_KEY: str = ""
    PINATA_SECRET_API_KEY: str = ""
    PINATA_JWT: str = ""
    PINATA_GATEWAY: str = "https://gateway.pinata.cloud/ipfs"
    MAX_UPLOAD_SIZE_MB: int = 500

    # CORS — comma-separated list, e.g. "http://localhost:5173,https://your-app.vercel.app"
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()