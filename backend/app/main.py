import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import models as models_router
from app.api import upload as upload_router
from app.core.config import get_settings
from app.db.session import Base, engine
from app.indexer.event_listener import EventListener

logging.basicConfig(level=logging.INFO)

listener = EventListener()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all is fine for a portfolio project; use Alembic migrations for anything
    # you'd call production.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Shared, connection-pooled client for outbound calls to Pinata — reused
    # across requests instead of opening a new connection each time.
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=120.0, write=300.0, pool=10.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
    )

    indexer_task = asyncio.create_task(listener.run_forever())
    yield
    listener.stop()
    await indexer_task
    await app.state.http_client.aclose()


app = FastAPI(title="AI Model Marketplace API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models_router.router)
app.include_router(upload_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}