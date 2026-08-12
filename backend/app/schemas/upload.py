from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_number: int
    ipfs_hash: str
    tx_hash: str
    created_at: datetime


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rater_address: str
    score: int
    created_at: datetime


class ModelListOut(BaseModel):
    """Slim shape for the marketplace grid — avoid shipping full version/rating history per card."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    on_chain_id: int
    owner_address: str
    name: str
    latest_ipfs_hash: str
    latest_version: int
    price_wei: int
    license_type: str
    avg_rating: float | None = None
    rating_count: int = 0


class ModelDetailOut(ModelListOut):
    description: str
    versions: list[VersionOut] = []
    ratings: list[RatingOut] = []


class PaginatedModels(BaseModel):
    items: list[ModelListOut]
    total: int
    page: int
    page_size: int
