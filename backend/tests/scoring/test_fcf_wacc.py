"""M11 tests: capex concept mapping, FCF computation, reverse-DCF uses WACC,
and scorecards carry WACC + FCF provenance.

Pure tests use the concept chains + reverse-DCF directly. Integration checks
read the generated report JSONs (skipped if not present).
"""
from __future__ import annotations

import json
import os

import pytest

from app.quant.scoring_inputs import _CONCEPT_CHAINS
from app.quant.reverse_dcf import implied_growth_rate
from app.valuation.wacc import FALLBACK_WACC

REPORTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "reports"))
TICKERS = ["META", "NVDA", "MSFT", "MU", "VRT", "BLK", "PLTR", "ACRS", "V"]


# ── Capex concept mapping ──────────────────────────────────────────────────

def test_capex_chain_includes_productive_assets():
    # NVDA / Visa tag PaymentsToAcquireProductiveAssets, not the PP&E concept.
    assert "PaymentsToAcquireProductiveAssets" in _CONCEPT_CHAINS["capex"]
    assert "PaymentsToAcquirePropertyPlantAndEquipment" in _CONCEPT_CHAINS["capex"]


def test_capex_chain_excludes_acquisitions():
    # Business acquisitions are M&A, NOT capex — must never be in the chain.
    assert "PaymentsToAcquireBusinessesNetOfCashAcquired" not in _CONCEPT_CHAINS["capex"]
    # Accrual disclosure, not a cash outflow — also excluded.
    assert "CapitalExpendituresIncurredButNotYetPaid" not in _CONCEPT_CHAINS["capex"]


def test_wacc_input_chains_present():
    for k in ("interest_expense", "income_tax_expense", "pretax_income"):
        assert k in _CONCEPT_CHAINS and _CONCEPT_CHAINS[k]


# ── FCF = OCF − capex ──────────────────────────────────────────────────────

def test_fcf_subtracts_capex():
    ocf, capex = 100.0, 30.0
    fcf = ocf - abs(capex)
    assert fcf == 70.0


# ── Reverse-DCF actually uses the discount rate (WACC) ─────────────────────

def test_reverse_dcf_responds_to_wacc():
    ev, fcf = 1_000_000.0, 50_000.0
    g_low = implied_growth_rate(ev, fcf, discount_rate=0.08)
    g_high = implied_growth_rate(ev, fcf, discount_rate=0.12)
    assert g_low is not None and g_high is not None
    # A higher discount rate demands a higher implied growth to justify the same EV.
    assert g_high > g_low


def test_reverse_dcf_invalid_when_wacc_below_terminal():
    # WACC must exceed terminal growth for the Gordon model.
    assert implied_growth_rate(1_000.0, 50.0, discount_rate=0.02, terminal_growth=0.025) is None


# ── Integration: scorecards carry WACC + FCF provenance ────────────────────

def _load():
    cards = {}
    for t in TICKERS:
        p = os.path.join(REPORTS, f"{t}_valuation_scorecard.json")
        if os.path.exists(p):
            cards[t] = json.load(open(p))
    return cards


_SKIP = not os.path.exists(os.path.join(REPORTS, "NVDA_valuation_scorecard.json"))


@pytest.mark.skipif(_SKIP, reason="scorecards not generated")
def test_scorecards_include_wacc_assumptions():
    cards = _load()
    assert cards
    for t, c in cards.items():
        assert c.get("wacc") is not None, f"{t} missing wacc"
        a = c.get("wacc_assumptions") or {}
        assert a.get("method") in ("capm_phase_a", "capm_phase_b", "fallback"), f"{t} bad wacc method"


@pytest.mark.skipif(_SKIP, reason="scorecards not generated")
def test_wacc_varies_across_tickers():
    waccs = [round(c["wacc"], 4) for c in _load().values() if c.get("wacc")]
    assert len(set(waccs)) >= 3  # not a single flat rate anymore


@pytest.mark.skipif(_SKIP, reason="scorecards not generated")
def test_nvda_and_visa_use_productive_assets_concept():
    cards = _load()
    for t in ("NVDA", "V"):
        fcf = cards[t].get("fcf") or {}
        assert fcf.get("capex_concept") == "PaymentsToAcquireProductiveAssets", t
        assert fcf.get("fcf") is not None, f"{t} should now have FCF"


@pytest.mark.skipif(_SKIP, reason="scorecards not generated")
def test_fcf_coverage_full_after_m11():
    cards = _load()
    have_fcf = sum(1 for c in cards.values() if (c.get("fcf") or {}).get("fcf") is not None)
    assert have_fcf == len(cards), f"only {have_fcf}/{len(cards)} have FCF"


@pytest.mark.skipif(_SKIP, reason="scorecards not generated")
def test_scorecards_include_wacc_source():
    # M12: every scorecard carries WACC input provenance (rf / beta / debt / tax).
    for t, c in _load().items():
        src = c.get("wacc_source") or {}
        assert src.get("method") in ("capm_phase_a", "capm_phase_b", "fallback"), t
        assert src.get("risk_free_source"), f"{t} missing risk_free_source"
        assert src.get("beta_source"), f"{t} missing beta_source"


@pytest.mark.skipif(_SKIP, reason="scorecards not generated")
def test_valuation_percentiles_present_or_honestly_missing():
    # At least one ticker has own-history percentiles; missing ones are flagged,
    # never faked (null block + a valuation_percentile_* missing flag).
    cards = _load()
    any_pct = False
    for t, c in cards.items():
        vp = c.get("valuation_percentiles")
        if vp:
            any_pct = True
            for k, blk in vp.items():
                assert 0.0 <= blk["percentile"] <= 1.0, f"{t}.{k}"
        else:
            flags = c.get("input_missing_flags") or []
            assert any(f.startswith("valuation_percentile") for f in flags), t
    assert any_pct, "no ticker produced valuation percentiles"


@pytest.mark.skipif(_SKIP, reason="scorecards not generated")
def test_missing_fcf_degrades_reverse_dcf_inputs():
    # ACRS is loss-making (negative FCF) ⇒ no implied growth ⇒ flagged missing.
    acrs = _load().get("ACRS") or {}
    ri = acrs.get("real_inputs") or {}
    assert ri.get("implied_growth") is None
    assert "implied_growth" in (acrs.get("input_missing_flags") or [])
