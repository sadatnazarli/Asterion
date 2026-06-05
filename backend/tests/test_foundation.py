"""Foundation smoke tests — verify the skeleton is coherent and importable.

These intentionally test contracts (config loads, 16 scores declared, walled
garden flags) rather than features (none implemented yet).
"""
from __future__ import annotations

from app.core.config import settings
from app.llm.provider_base import ChatProvider, ChatRequest, Message
from app.scoring.registry import SCORES, SCORES_BY_KEY


def test_config_loads_with_local_first_defaults() -> None:
    assert settings.llm_backend in {"ollama", "openai_compatible"}
    assert settings.allow_external_llm is False  # local-first default
    assert settings.embed_dim == 768
    assert "postgresql" in settings.db_dsn


def test_exactly_sixteen_scores() -> None:
    assert len(SCORES) == 16
    assert len(SCORES_BY_KEY) == 16


def test_walled_garden_separation() -> None:
    invest = SCORES_BY_KEY["final_investment"]
    trade = SCORES_BY_KEY["final_trading"]
    assert invest.regime_aware is True
    assert trade.walled_trading is True
    assert trade.sector_relative is False


def test_chat_request_defaults_to_json_mode() -> None:
    req = ChatRequest(messages=[Message("user", "hi")], model="qwen2.5:7b-instruct")
    assert req.json_mode is True  # strict JSON by default
    assert hasattr(ChatProvider, "chat")
