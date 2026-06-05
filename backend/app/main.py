"""Asterion FastAPI application entrypoint."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import stream, system, ui
from app.core.config import get_settings, load_env_files
from app.market.router import router as market_router

_settings = get_settings()
logging.basicConfig(level=getattr(logging, _settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("asterion")

app = FastAPI(
    title="Asterion",
    version="0.1.0",
    description=(
        "Local-first institutional-grade equity intelligence & portfolio "
        "decision engine. Deterministic math is the skeleton; the local LLM is "
        "the analyst, not the oracle."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ui.router, prefix="/api", tags=["ui"])
app.include_router(market_router, prefix="/api/market", tags=["market"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(stream.router, tags=["stream"])


@app.on_event("startup")
def log_provider_config() -> None:
    loaded = load_env_files()
    settings = get_settings()
    diag = settings.env_diagnostics()
    logger.info("ENV cwd=%s", diag["cwd"])
    logger.info("ENV backend_root=%s", diag["backend_root"])
    logger.info("ENV loaded_files=%s", diag["loaded_env_files"])
    logger.info("ENV FINNHUB_API_KEY present=%s", diag["FINNHUB_API_KEY_present"])
    logger.info("ENV ASTERION_FINNHUB_API_KEY present=%s", diag["ASTERION_FINNHUB_API_KEY_present"])
    logger.info(
        "Finnhub configured=%s masked_key=%s",
        diag["finnhub_configured"],
        diag["finnhub_masked_key"],
    )
    if not diag["finnhub_configured"]:
        logger.warning(
            "Finnhub key missing. Add FINNHUB_API_KEY or ASTERION_FINNHUB_API_KEY to %s/.env",
            diag["backend_root"],
        )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "asterion", "env": get_settings().env}


@app.get("/config", tags=["system"])
def config_introspection() -> dict[str, object]:
    settings = get_settings()
    return {
        "env": settings.env,
        "llm_enabled": settings.llm_enabled,
        "llm_backend": settings.llm_backend,
        "llm_model": settings.llm_model,
        "embed_model": settings.embed_model,
        "embed_dim": settings.embed_dim,
        "allow_external_llm": settings.allow_external_llm,
        "prices_provider": settings.prices_provider,
        "finnhub_configured": bool(settings.finnhub_api_key),
        "local_first": True,
    }
