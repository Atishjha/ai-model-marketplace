from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Model, Rating
from app.db.session import get_db
from app.schemas.model import ModelDetailOut, PaginatedModels

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=PaginatedModels)
async def list_models(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(None, description="Search model name/description"),
    license_type: str | None = None,
    owner_address: str | None = None,
    min_price_wei: int | None = None,
    max_price_wei: int | None = None,
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|rating)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    avg_rating_subq = (
        select(Rating.model_id, func.avg(Rating.score).label("avg_rating"), func.count(Rating.id).label("rating_count"))
        .group_by(Rating.model_id)
        .subquery()
    )

    stmt = select(
        Model,
        avg_rating_subq.c.avg_rating,
        avg_rating_subq.c.rating_count,
    ).outerjoin(avg_rating_subq, Model.id == avg_rating_subq.c.model_id)

    if q:
        like = f"%{q}%"
        stmt = stmt.where(Model.name.ilike(like) | Model.description.ilike(like))
    if license_type:
        stmt = stmt.where(Model.license_type == license_type)
    if owner_address:
        stmt = stmt.where(Model.owner_address == owner_address)
    if min_price_wei is not None:
        stmt = stmt.where(Model.price_wei >= min_price_wei)
    if max_price_wei is not None:
        stmt = stmt.where(Model.price_wei <= max_price_wei)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    if sort == "price_asc":
        stmt = stmt.order_by(Model.price_wei.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(Model.price_wei.desc())
    elif sort == "rating":
        stmt = stmt.order_by(avg_rating_subq.c.avg_rating.desc().nulls_last())
    else:
        stmt = stmt.order_by(Model.created_at.desc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()

    items = []
    for model, avg_rating, rating_count in rows:
        item = {
            **model.__dict__,
            "avg_rating": float(avg_rating) if avg_rating is not None else None,
            "rating_count": rating_count or 0,
        }
        items.append(item)

    return PaginatedModels(items=items, total=total, page=page, page_size=page_size)


@router.get("/{model_id}", response_model=ModelDetailOut)
async def get_model_detail(model_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Model)
        .where(Model.id == model_id)
        .options(selectinload(Model.versions), selectinload(Model.ratings))
    )
    model = (await db.execute(stmt)).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")

    scores = [r.score for r in model.ratings]
    avg_rating = sum(scores) / len(scores) if scores else None

    return ModelDetailOut(
        **{k: v for k, v in model.__dict__.items() if not k.startswith("_")},
        avg_rating=avg_rating,
        rating_count=len(scores),
        versions=model.versions,
        ratings=model.ratings,
    )
