"""M8.9 — daily contribution calculation (why did the portfolio move today)."""
from app.api.routes.ui import compute_contributors


def _live():
    return {
        "total_value": 1000.0,
        "daily_pnl": -8.0,
        "holdings": [
            {"ticker": "META", "current_value": 200.0, "daily_change_pct": 2.0, "theme": "mega-cap tech"},   # +4.0
            {"ticker": "MSFT", "current_value": 100.0, "daily_change_pct": 1.0, "theme": "mega-cap tech"},   # +1.0
            {"ticker": "PLTR", "current_value": 100.0, "daily_change_pct": -5.0, "theme": "AI/software"},    # -5.0
            {"ticker": "NVDA", "current_value": 200.0, "daily_change_pct": -4.0, "theme": "AI/semiconductor"},  # -8.0
            {"ticker": "FLAT", "current_value": 400.0, "daily_change_pct": 0.0, "theme": "core index"},      # 0.0
        ],
    }


def test_contribution_formula():
    out = compute_contributors(_live())
    by = {r["ticker"]: r for r in out["all"]}
    assert by["META"]["estimated_contribution_dollars"] == 4.0
    assert by["NVDA"]["estimated_contribution_dollars"] == -8.0
    assert by["FLAT"]["direction"] == "flat"


def test_top_positive_and_negative_ranked():
    out = compute_contributors(_live())
    pos = [r["ticker"] for r in out["top_positive"]]
    neg = [r["ticker"] for r in out["top_negative"]]
    assert pos[0] == "META"  # biggest positive first
    assert neg[0] == "NVDA"  # biggest drag first
    assert "PLTR" in neg


def test_sum_and_unexplained_difference():
    out = compute_contributors(_live())
    # 4 + 1 - 5 - 8 + 0 = -8.0
    assert out["sum_contributions"] == -8.0
    assert out["daily_pnl_reported"] == -8.0
    assert abs(out["unexplained_difference"]) < 1e-9


def test_handles_missing_change_pct():
    live = {"total_value": 100.0, "daily_pnl": 0.0, "holdings": [{"ticker": "X", "current_value": 100.0, "daily_change_pct": None}]}
    out = compute_contributors(live)
    assert out["all"][0]["estimated_contribution_dollars"] == 0.0
