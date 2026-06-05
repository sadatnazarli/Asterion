import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings, mask_api_key


def test_mask_api_key():
    assert mask_api_key("abcdefghij") == "****ghij"
    assert mask_api_key("ab") == "****"
    assert mask_api_key(None) is None


def test_finnhub_env_alias(monkeypatch):
    monkeypatch.delenv("ASTERION_FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    get_settings.cache_clear()
    monkeypatch.setenv("FINNHUB_API_KEY", "test_finnhub_key_1234")
    s = Settings()
    assert s.finnhub_api_key == "test_finnhub_key_1234"
    get_settings.cache_clear()


def test_asterion_finnhub_env_alias(monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    get_settings.cache_clear()
    monkeypatch.setenv("ASTERION_FINNHUB_API_KEY", "asterion_key_9999")
    s = Settings()
    assert s.finnhub_api_key == "asterion_key_9999"
    get_settings.cache_clear()


def test_providers_shows_finnhub_active(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "secret_finnhub_key_abc1")
    get_settings.cache_clear()
    import importlib
    import app.api.routes.system as system_mod
    import app.main as main_mod
    importlib.reload(system_mod)
    importlib.reload(main_mod)
    client = TestClient(main_mod.app)
    res = client.get("/api/system/providers")
    assert res.status_code == 200
    data = res.json()
    assert data["finnhub"]["configured"] is True
    assert data["finnhub"]["status"] == "ok"
    assert data["finnhub"]["masked_key"] == "****abc1"
    assert "FINNHUB_API_KEY" in data["finnhub"]["env_variables"]
    body = res.text
    assert "secret_finnhub_key_abc1" not in body
    get_settings.cache_clear()


def test_providers_shows_env_hint_when_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("ASTERION_FINNHUB_API_KEY", raising=False)
    empty_env = tmp_path / ".env"
    empty_env.write_text("ASTERION_SEC_USER_AGENT=test\n")
    monkeypatch.setattr("app.core.config.BACKEND_ROOT", tmp_path)
    monkeypatch.setattr("app.core.config.PROJECT_ROOT", tmp_path)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.finnhub_api_key is None
    from app.api.routes.system import _provider_block, ENV_HINTS
    block = _provider_block(None, ENV_HINTS["finnhub"])
    assert block["configured"] is False
    assert "FINNHUB_API_KEY" in block["setup_hint"]
    get_settings.cache_clear()


def test_ws_accepts_tickers_and_emits_status(monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("ASTERION_FINNHUB_API_KEY", raising=False)
    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    with client.websocket_connect("/ws/quotes?tickers=MSFT,NVDA") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "stream_status"
        assert msg["status"] in ("fallback", "connected", "disconnected")
        assert "provider" in msg
    get_settings.cache_clear()
