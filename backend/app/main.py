"""Slidelang FastAPI app entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import compile as compile_route
from app.routes import decks, generate, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Slidelang API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(compile_route.router, prefix="/api", tags=["compile"])
app.include_router(decks.router, prefix="/api", tags=["decks"])


@app.get("/")
async def root():
    return {"name": "Slidelang API", "version": "0.1.0", "docs": "/docs"}
