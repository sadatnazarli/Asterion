"""M12 tests: FRED risk-free + FMP beta providers, fallbacks, and no key leaks.

All network is monkeypatched — these never hit FRED/FMP. The cache path is
redirected to a tmp file so a developer's real cache can't change the result.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

import app.market.fred_provider as fred
import app.market.beta_provider as betap
from app.valuation.wacc import compute_wacc, beta_for_symbol


@dataclass
class _FakeSettings:
    fred_api_key: str | None = None
    fmp_api_key: str | None = None


class _FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


# ── FRED: fallback when no key ─────────────────────────────────────────────

def test_fred_fallback_without_key(tmp_path, monkeypatch):
    monkeypatch.setattr(fred, "_CACHE_PATH", tmp_path / "macro.json")
    monkeypatch.setattr(fred, "get_settings", lambda: _FakeSettings(fred_api_key=None))
    r = fred.get_risk_free_rate(force_refresh=True)
    assert r.source == "fallback"
    assert r.risk_free_rate == fred.DEFAULT_RISK_FREE_RATE
    assert r.as_of is None


# ── FRED: parses a live observation, converts percent → decimal ────────────

def test_fred_uses_live_rate(tmp_path, monkeypatch):
    monkeypatch.setattr(fred, "_CACHE_PATH", tmp_path / "macro.json")
    monkeypatch.setattr(fred, "get_settings", lambda: _FakeSettings(fred_api_key="SECRET_FRED"))
    payload = {"observations": [
        {"date": "2026-06-03", "value": "."},          # holiday, skipped
        {"date": "2026-06-02", "value": "4.35"},        # used
    ]}
    monkeypatch.setattr(fred.requests, "get", lambda *a, **k: _FakeResp(200, payload))
    r = fred.get_risk_free_rate(force_refresh=True)
    assert r.source == "fred:DGS10"
    assert r.risk_free_rate == pytest.approx(0.0435)
    assert r.as_of == "2026-06-02"
    # no key leak in the result or its dict
    assert "SECRET_FRED" not in json.dumps(r.as_dict())


def test_fred_uses_cache(tmp_path, monkeypatch):
    cache = tmp_path / "macro.json"
    monkeypatch.setattr(fred, "_CACHE_PATH", cache)
    import time
    cache.write_text(json.dumps({"risk_free_rate": 0.041, "as_of": "2026-05-30",
                                 "series_id": "DGS10", "_cached_at": time.time()}))
    r = fred.get_risk_free_rate()
    assert r.source == "fred_cache:DGS10"
    assert r.risk_free_rate == pytest.approx(0.041)


# ── Beta: fallback to sector when no FMP key ───────────────────────────────

def test_beta_sector_fallback_without_key(tmp_path, monkeypatch):
    monkeypatch.setattr(betap, "_CACHE_PATH", tmp_path / "beta.json")
    monkeypatch.setattr(betap, "get_settings", lambda: _FakeSettings(fmp_api_key=None))
    r = betap.get_beta("NVDA")
    exp_beta, exp_source = beta_for_symbol("NVDA")
    assert r.beta == exp_beta
    assert r.source == exp_source == "sector_fallback:semiconductor"


def test_beta_uses_provider_when_key(tmp_path, monkeypatch):
    monkeypatch.setattr(betap, "_CACHE_PATH", tmp_path / "beta.json")
    monkeypatch.setattr(betap, "get_settings", lambda: _FakeSettings(fmp_api_key="SECRET_FMP"))
    monkeypatch.setattr(betap.requests, "get", lambda *a, **k: _FakeResp(200, [{"beta": 1.73}]))
    r = betap.get_beta("NVDA")
    assert r.beta == pytest.approx(1.73)
    assert r.source == "provider_beta:fmp"
    assert "SECRET_FMP" not in json.dumps(r.as_dict())


def test_beta_rejects_implausible_provider_value(tmp_path, monkeypatch):
    monkeypatch.setattr(betap, "_CACHE_PATH", tmp_path / "beta.json")
    monkeypatch.setattr(betap, "get_settings", lambda: _FakeSettings(fmp_api_key="K"))
    monkeypatch.setattr(betap.requests, "get", lambda *a, **k: _FakeResp(200, [{"beta": 99.0}]))
    r = betap.get_beta("MSFT")  # absurd beta rejected → sector fallback
    assert r.source.startswith("sector_fallback")


# ── WACC consumes the live inputs and labels the phase ─────────────────────

def test_wacc_phase_b_with_fred_rate():
    r = compute_wacc(
        market_cap=1000.0, total_debt=0.0, beta=1.1, beta_source="sector_fallback:x",
        interest_expense=None, income_tax=None, pretax_income=None,
        risk_free_rate=0.0435, risk_free_source="fred:DGS10",
    )
    assert r.method == "capm_phase_b"
    assert r.risk_free_rate == pytest.approx(0.0435)
    assert r.risk_free_source == "fred:DGS10"
    # Ke = rf + beta*ERP uses the FRED rate
    assert r.cost_of_equity == pytest.approx(0.0435 + 1.1 * 0.05)


def test_wacc_phase_b_with_provider_beta():
    r = compute_wacc(
        market_cap=1000.0, total_debt=0.0, beta=1.73, beta_source="provider_beta:fmp",
        interest_expense=None, income_tax=None, pretax_income=None,
    )
    assert r.method == "capm_phase_b"
    assert r.beta == pytest.approx(1.73)


def test_wacc_phase_a_when_all_static():
    r = compute_wacc(
        market_cap=1000.0, total_debt=0.0, beta=1.1, beta_source="sector_fallback:x",
        interest_expense=None, income_tax=None, pretax_income=None,
    )
    assert r.method == "capm_phase_a"
    assert r.risk_free_source == "static_default"
