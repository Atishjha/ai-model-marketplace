from datetime import datetime

from pydantic import BaseModel


class ModelSummary(BaseModel):
    id: int
    name: str
    owner_address: str
    license_type: str
    price_wei: int
    average_rating: float
    rating_count: int
    registered_at: datetime

    @classmethod
    def from_orm_model(cls, m) -> "ModelSummary":
        return cls(
            id=m.id,
            name=m.name,
            owner_address=m.owner_address,
            license_type=m.license_type,
            price_wei=int(m.price_wei),
            average_rating=m.average_rating,
            rating_count=m.rating_count,
            registered_at=m.registered_at,
        )


class VersionSummary(BaseModel):
    version_index: int
    ipfs_hash: str
    note: str
    published_at: datetime


class ModelDetail(ModelSummary):
    current_ipfs_hash: str
    versions: list[VersionSummary]

    @classmethod
    def from_orm_model(cls, m) -> "ModelDetail":
        return cls(
            id=m.id,
            name=m.name,
            owner_address=m.owner_address,
            license_type=m.license_type,
            price_wei=int(m.price_wei),
            average_rating=m.average_rating,
            rating_count=m.rating_count,
            registered_at=m.registered_at,
            current_ipfs_hash=m.current_ipfs_hash,
            versions=[
                VersionSummary(
                    version_index=v.version_index,
                    ipfs_hash=v.ipfs_hash,
                    note=v.note,
                    published_at=v.published_at,
                )
                for v in m.versions
            ],
        )