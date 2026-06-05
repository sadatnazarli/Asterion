from fastapi import APIRouter

from app.core.config import get_settings, mask_api_key
from app.market.provider_state import finnhub_last_success_at

router = APIRouter()

ENV_HINTS = {
    "finnhub": ["FINNHUB_API_KEY", "ASTERION_FINNHUB_API_KEY"],
    "fmp": ["FMP_API_KEY", "ASTERION_FMP_API_KEY"],
    "fred": ["FRED_API_KEY", "ASTERION_FRED_API_KEY"],
    "polygon": ["POLYGON_API_KEY", "ASTERION_POLYGON_API_KEY"],
    "openfigi": ["OPENFIGI_API_KEY", "ASTERION_OPENFIGI_API_KEY"],
}


def _provider_block(key: str | None, env_names: list[str], *, last_success_at: str | None = None) -> dict:
    configured = bool(key)
    return {
        "configured": configured,
        "status": "ok" if configured else "not_configured",
        "masked_key": mask_api_key(key),
        "last_success_at": last_success_at,
        "env_variables": env_names,
        "setup_hint": None
        if configured
        else f"Add one of: {', '.join(env_names)} to backend/.env or project .env",
    }


@router.get("/providers")
def get_providers():
    settings = get_settings()
    finnhub_ok = bool(settings.finnhub_api_key)
    return {
        "finnhub": {
            **_provider_block(
                settings.finnhub_api_key,
                ENV_HINTS["finnhub"],
                last_success_at=finnhub_last_success_at(),
            ),
            "streaming": finnhub_ok,
            "websocket": "wss://ws.finnhub.io (server-side only)",
        },
        "fmp": _provider_block(settings.fmp_api_key, ENV_HINTS["fmp"]),
        "fred": _provider_block(settings.fred_api_key, ENV_HINTS["fred"]),
        "polygon": _provider_block(settings.polygon_api_key, ENV_HINTS["polygon"]),
        "openfigi": _provider_block(settings.openfigi_api_key, ENV_HINTS["openfigi"]),
        "yfinance": {
            "configured": True,
            "status": "fallback",
            "streaming": False,
            "note": "Delayed polling only — not real-time",
        },
        "live_stream": {
            "available": finnhub_ok,
            "endpoint": "/ws/quotes?tickers=MSFT,NVDA,...",
            "mode": "finnhub_ws" if finnhub_ok else "polling_fallback",
        },
    }


@router.get("/env-diagnostics")
def env_diagnostics():
    """Safe env diagnostics — never returns raw secrets."""
    return get_settings().env_diagnostics()
