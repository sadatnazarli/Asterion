"""M12: Phase-B macro valuation layer — FRED risk-free + FMP beta + percentiles.

Regenerates the 9-ticker scorecards with:
  - risk-free rate from FRED (DGS10) when FRED_API_KEY is set, else static 4.5%
  - beta from FMP when FMP_API_KEY is set, else the Phase-A sector fallback
  - historical valuation percentiles (own 3–6Y P/E, EV/Revenue, P/FCF)

Emits:
  - reports/macro_inputs.{md,json}          — FRED status + risk-free used
  - reports/beta_sources.{md,json}          — beta + provenance per ticker
  - reports/wacc_phase_b_summary.{md,json}  — WACC before (Phase A) vs after
  - reports/<T>_valuation_scorecard.json    — regenerated scorecards

Usage:
    cd backend && .venv/bin/python ../scripts/macro_wacc_phase_b.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import psycopg  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.backtesting.dataset import load_price_history  # noqa: E402
from app.market.beta_provider import get_beta, fmp_configured  # noqa: E402
from app.market.fred_provider import get_risk_free_rate, fred_configured  # noqa: E402
from app.scoring.scorecard_generator import generate_real_scorecard  # noqa: E402

TICKERS = ["META", "NVDA", "MSFT", "MU", "VRT", "BLK", "PLTR", "ACRS", "V"]
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
# ~6 calendar years — enough to price 5–6 fiscal period-ends for percentiles.
PCT_LOOKBACK_DAYS = 2200


def _pct(x):
    return f"{x*100:.2f}%" if isinstance(x, (int, float)) else "—"


def _load_phase_a_wacc() -> dict[str, float]:
    """Phase-A WACC per ticker from the M11 summary (the 'before' column)."""
    path = os.path.join(REPORTS_DIR, "wacc_summary.json")
    try:
        rows = json.load(open(path)).get("rows", [])
    except (FileNotFoundError, ValueError):
        return {}
    return {r["ticker"]: r.get("wacc") for r in rows if r.get("wacc") is not None}


def main() -> int:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    phase_a = _load_phase_a_wacc()

    macro = get_risk_free_rate()
    beta_rows, wacc_rows, pct_rows = [], [], []

    with psycopg.connect(settings.db_dsn_sync) as conn:
        for t in TICKERS:
            bars = load_price_history(t, lookback_days=PCT_LOOKBACK_DAYS)
            price_bars = [(b.d, b.close) for b in bars]
            closes = [b.close for b in bars][-300:]  # recent window for vol/drawdown

            sc = generate_real_scorecard(
                conn, t, price_history=closes or None, price_bars=price_bars or None,
            )
            # persist regenerated scorecard JSON
            with open(os.path.join(REPORTS_DIR, f"{t}_valuation_scorecard.json"), "w") as fh:
                json.dump(sc, fh, indent=2)

            br = get_beta(t)
            beta_rows.append({"ticker": t, "beta": br.beta, "source": br.source})

            w = sc.get("wacc_assumptions") or {}
            wacc_rows.append({
                "ticker": t,
                "wacc_before": phase_a.get(t),
                "wacc_after": sc.get("wacc"),
                "method": w.get("method"),
                "risk_free_rate": w.get("risk_free_rate"),
                "risk_free_source": w.get("risk_free_source"),
                "beta": w.get("beta"),
                "beta_source": w.get("beta_source"),
                "cost_of_equity": w.get("cost_of_equity"),
                "cost_of_debt": w.get("cost_of_debt"),
                "cost_of_debt_source": w.get("cost_of_debt_source"),
                "tax_rate": w.get("tax_rate"),
                "tax_rate_source": w.get("tax_rate_source"),
                "confidence": w.get("confidence"),
            })

            vp = sc.get("valuation_percentiles") or {}
            pct_rows.append({
                "ticker": t,
                "pe": (vp.get("pe") or {}).get("percentile"),
                "pe_n": (vp.get("pe") or {}).get("n_years"),
                "ev_revenue": (vp.get("ev_revenue") or {}).get("percentile"),
                "ev_rev_n": (vp.get("ev_revenue") or {}).get("n_years"),
                "p_fcf": (vp.get("p_fcf") or {}).get("percentile"),
                "p_fcf_n": (vp.get("p_fcf") or {}).get("n_years"),
            })

    # ── macro_inputs ─────────────────────────────────────────────────────
    macro_payload = {"generated_at": now, "fred_configured": fred_configured(),
                     **macro.as_dict()}
    json.dump(macro_payload, open(os.path.join(REPORTS_DIR, "macro_inputs.json"), "w"), indent=2)
    md = "# Macro Inputs — Phase B (M12)\n\n"
    md += f"_Generated {now}._\n\n"
    md += f"- FRED configured: **{fred_configured()}**\n"
    md += f"- Risk-free rate (10Y UST, DGS10): **{_pct(macro.risk_free_rate)}**\n"
    md += f"- Source: `{macro.source}`" + (f" (as of {macro.as_of})" if macro.as_of else "") + "\n"
    md += f"- Series: `{macro.series_id}`\n\n"
    if macro.source == "fallback":
        md += "> FRED unavailable (no key or call failed) — using the static 4.5% "
        md += "fallback. Set `FRED_API_KEY` in `backend/.env` for the live 10Y.\n"
    else:
        md += "> Live FRED 10Y, cached 12h in `data/cache/macro.json`. ERP stays a "
        md += "documented 5.0% assumption (not derived).\n"
    open(os.path.join(REPORTS_DIR, "macro_inputs.md"), "w").write(md)

    # ── beta_sources ─────────────────────────────────────────────────────
    json.dump({"generated_at": now, "fmp_configured": fmp_configured(), "rows": beta_rows},
              open(os.path.join(REPORTS_DIR, "beta_sources.json"), "w"), indent=2)
    md = "# Beta Sources — Phase B (M12)\n\n"
    md += f"_Generated {now}._\n\n"
    md += f"- FMP configured: **{fmp_configured()}**\n\n"
    md += "| Ticker | Beta | Source |\n|---|---|---|\n"
    for r in beta_rows:
        md += f"| {r['ticker']} | {r['beta']} | `{r['source']}` |\n"
    md += "\n> `provider_beta:fmp` = live FMP beta; `sector_fallback:<theme>` = "
    md += "Phase-A theme beta (no FMP key or call failed); `default` = unmapped 1.10.\n"
    open(os.path.join(REPORTS_DIR, "beta_sources.md"), "w").write(md)

    # ── wacc_phase_b_summary ─────────────────────────────────────────────
    json.dump({"generated_at": now, "macro": macro.as_dict(), "rows": wacc_rows,
               "percentiles": pct_rows},
              open(os.path.join(REPORTS_DIR, "wacc_phase_b_summary.json"), "w"), indent=2)
    md = "# Dynamic WACC — Phase B Summary (M12)\n\n"
    md += f"_Generated {now}._\n\n"
    md += f"Risk-free `{macro.source}` = {_pct(macro.risk_free_rate)}; ERP 5.0% (assumption); "
    md += "beta from FMP when configured else sector fallback; cost of debt & tax from SEC facts.\n\n"
    md += "| Ticker | WACC before (A) | WACC after (B) | Δ | Method | Rf (src) | Beta (src) | Conf |\n"
    md += "|---|---|---|---|---|---|---|---|\n"
    for r in wacc_rows:
        before, after = r["wacc_before"], r["wacc_after"]
        delta = _pct(after - before) if (isinstance(after, (int, float)) and isinstance(before, (int, float))) else "—"
        bs = (r["beta_source"] or "").replace("sector_fallback:", "sf:")
        md += (f"| {r['ticker']} | {_pct(before)} | {_pct(after)} | {delta} | "
               f"{r['method']} | {_pct(r['risk_free_rate'])} ({r['risk_free_source']}) | "
               f"{r['beta']} ({bs}) | {r['confidence']} |\n")
    md += "\n## Own-history valuation percentiles\n\n"
    md += "Percentile of today's multiple vs the ticker's own 3–6Y history "
    md += "(1.00 = richest ever, 0.00 = cheapest). `—` = insufficient history (not faked).\n\n"
    md += "| Ticker | P/E %ile (n) | EV/Rev %ile (n) | P/FCF %ile (n) |\n|---|---|---|---|\n"
    for r in pct_rows:
        def cell(p, n):
            return f"{p:.2f} ({n})" if isinstance(p, (int, float)) else "—"
        md += f"| {r['ticker']} | {cell(r['pe'], r['pe_n'])} | {cell(r['ev_revenue'], r['ev_rev_n'])} | {cell(r['p_fcf'], r['p_fcf_n'])} |\n"
    open(os.path.join(REPORTS_DIR, "wacc_phase_b_summary.md"), "w").write(md)

    print(f"Risk-free: {_pct(macro.risk_free_rate)} ({macro.source}); "
          f"FRED={fred_configured()} FMP={fmp_configured()}")
    print("Wrote macro_inputs / beta_sources / wacc_phase_b_summary (.md/.json) + 9 scorecards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
