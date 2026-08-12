from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Model(Base):
    """Mirrors ModelRegistry.sol's model struct — one row per registered model."""

    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True)
    on_chain_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)  # id/tokenId from the contract
    owner_address: Mapped[str] = mapped_column(String(42), index=True)
    latest_ipfs_hash: Mapped[str] = mapped_column(String(100))
    latest_version: Mapped[int] = mapped_column(default=1)
    price_wei: Mapped[int] = mapped_column(Numeric(78, 0))  # uint256 doesn't fit in BigInteger
    license_type: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(String(2000), default="")
    registered_at_block: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    versions: Mapped[list["ModelVersion"]] = relationship(
        back_populates="model", cascade="all, delete-orphan", order_by="ModelVersion.version_number"
    )
    ratings: Mapped[list["Rating"]] = relationship(back_populates="model", cascade="all, delete-orphan")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class ModelVersion(Base):
    """Append-only version history — one row per updateVersion() event."""

    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("model_id", "version_number", name="uq_model_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    version_number: Mapped[int] = mapped_column()
    ipfs_hash: Mapped[str] = mapped_column(String(100))
    tx_hash: Mapped[str] = mapped_column(String(66))
    block_number: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    model: Mapped["Model"] = relationship(back_populates="versions")


class Purchase(Base):
    """Mirrors LicensePurchased events — used to gate who's allowed to rate."""

    __tablename__ = "purchases"
    __table_args__ = (UniqueConstraint("model_id", "buyer_address", name="uq_model_buyer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    buyer_address: Mapped[str] = mapped_column(String(42), index=True)
    price_paid_wei: Mapped[int] = mapped_column(Numeric(78, 0))
    tx_hash: Mapped[str] = mapped_column(String(66))
    block_number: Mapped[int] = mapped_column(BigInteger)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    model: Mapped["Model"] = relationship(back_populates="purchases")


class Rating(Base):
    """Mirrors Rated events. Contract enforces buyer-only rating; we just mirror it."""

    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("model_id", "rater_address", name="uq_model_rater"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    rater_address: Mapped[str] = mapped_column(String(42), index=True)
    score: Mapped[int] = mapped_column()  # e.g. 1-5
    tx_hash: Mapped[str] = mapped_column(String(66))
    block_number: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    model: Mapped["Model"] = relationship(back_populates="ratings")


class IndexerState(Base):
    """Single-row (per event listener) checkpoint so restarts resume, not rescan from genesis."""

    __tablename__ = "indexer_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    listener_name: Mapped[str] = mapped_column(String(100), unique=True)
    last_processed_block: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
