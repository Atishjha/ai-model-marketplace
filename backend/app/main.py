import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import models as models_router
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

    indexer_task = asyncio.create_task(listener.run_forever())
    yield
    listener.stop()
    await indexer_task


app = FastAPI(title="AI Model Marketplace API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server; add your deployed frontend origin too
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models_router.router)
# app.include_router(upload.router)   # Phase 2
# app.include_router(purchase.router) # Phase 4 tx-building endpoint


@app.get("/health")
async def health():
    return {"status": "ok"}
