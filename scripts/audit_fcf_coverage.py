"""M11: audit capex/FCF coverage and emit the dynamic-WACC summary.

Produces:
  - reports/fcf_coverage_audit.{md,json}  — OCF / capex / FCF availability per
    ticker, BEFORE (old capex chain) vs AFTER (M11 broadened chain), the source
    concept used, and any still-missing XBRL concepts.
  - reports/wacc_summary.{md,json}        — Phase-A WACC per ticker with the full
    assumption set (beta/source, cost of debt, tax rate, weights, confidence).

Usage:
    .venv/bin/python ../scripts/audit_fcf_coverage.py
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
from app.quant.scoring_inputs import (  # noqa: E402
    _CONCEPT_CHAINS, detect_concept, get_annual_periods,
)
from app.scoring.scorecard_generator import (  # noqa: E402
    generate_real_scorecard, resolve_company,
)

TICKERS = ["META", "NVDA", "MSFT", "MU", "VRT", "BLK", "PLTR", "ACRS", "V"]
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))

# Capex chain as it stood BEFORE M11 (to measure the coverage delta).
OLD_CAPEX_CHAIN = ["PaymentsToAcquirePropertyPlantAndEquipment", "CapitalExpenditure"]


def audit_one(conn, symbol: str) -> dict:
    company_id, _ = resolve_company(conn, symbol)
    if company_id is None:
        return {"ticker": symbol, "error": "ticker_not_found"}
    periods = get_annual_periods(conn, company_id, limit=12)
    # canonical newest FY (dedup by fiscal_year, keep latest period_end)
    seen, fy_periods = set(), []
    for p in periods:
        if p["fiscal_year"] in seen:
            continue
        seen.add(p["fiscal_year"])
        fy_periods.append(p)
    newest = fy_periods[0]
    pe, fy, fp = newest["period_end"], newest["fiscal_year"], newest["fiscal_period"]

    ocf_concept = detect_concept(conn, company_id, _CONCEPT_CHAINS["operating_cash_flow"], pe, fiscal_year=fy, fiscal_period=fp)
    capex_old = detect_concept(conn, company_id, OLD_CAPEX_CHAIN, pe, fiscal_year=fy, fiscal_period=fp)
    capex_new = detect_concept(conn, company_id, _CONCEPT_CHAINS["capex"], pe, fiscal_year=fy, fiscal_period=fp)

    return {
        "ticker": symbol,
        "fiscal_year": fy,
        "ocf_available": ocf_concept is not None,
        "ocf_concept": ocf_concept,
        "capex_before": capex_old,
        "capex_after": capex_new,
        "fcf_before": (ocf_concept is not None and capex_old is not None),
        "fcf_after": (ocf_concept is not None and capex_new is not None),
        "unlocked_by_m11": (capex_old is None and capex_new is not None),
        "missing_concepts": [
            name for name, ok in [
                ("operating_cash_flow", ocf_concept is not None),
                ("capex", capex_new is not None),
            ] if not ok
        ],
    }


def main() -> int:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    audit_rows, wacc_rows = [], []
    with psycopg.connect(settings.db_dsn_sync) as conn:
        for t in TICKERS:
            audit_rows.append(audit_one(conn, t))
            closes = [b.close for b in load_price_history(t, lookback_days=400)]
            sc = generate_real_scorecard(conn, t, price_history=closes or None)
            f = sc.get("fcf", {})
            w = sc.get("wacc_assumptions") or {}
            wacc_rows.append({
                "ticker": t,
                "wacc": sc.get("wacc"),
                "method": w.get("method"),
                "beta": w.get("beta"),
                "beta_source": w.get("beta_source"),
                "cost_of_equity": w.get("cost_of_equity"),
                "cost_of_debt": w.get("cost_of_debt"),
                "cost_of_debt_source": w.get("cost_of_debt_source"),
                "tax_rate": w.get("tax_rate"),
                "tax_rate_source": w.get("tax_rate_source"),
                "weight_equity": w.get("weight_equity"),
                "weight_debt": w.get("weight_debt"),
                "confidence": w.get("confidence"),
                "fcf": f.get("fcf"),
                "fcf_margin": f.get("fcf_margin"),
            })

    # ── FCF coverage report ──────────────────────────────────────────────
    before_n = sum(1 for r in audit_rows if r.get("fcf_before"))
    after_n = sum(1 for r in audit_rows if r.get("fcf_after"))
    fcf_payload = {
        "generated_at": now, "tickers": TICKERS,
        "fcf_coverage_before": before_n, "fcf_coverage_after": after_n,
        "total": len(TICKERS), "rows": audit_rows,
    }
    with open(os.path.join(REPORTS_DIR, "fcf_coverage_audit.json"), "w") as fh:
        json.dump(fcf_payload, fh, indent=2)

    md = "# FCF Coverage Audit (M11)\n\n"
    md += f"_Generated {now}._\n\n"
    md += f"**FCF computable: {before_n}/{len(TICKERS)} before → {after_n}/{len(TICKERS)} after** "
    md += "broadening the capex concept chain (added `PaymentsToAcquireProductiveAssets` "
    md += "et al.). Acquisitions are NOT counted as capex.\n\n"
    md += "| Ticker | FY | OCF | Capex before | Capex after | FCF before | FCF after | Unlocked by M11 | Missing |\n"
    md += "|---|---|---|---|---|---|---|---|---|\n"
    for r in audit_rows:
        if r.get("error"):
            md += f"| {r['ticker']} | — | — | — | — | — | — | — | {r['error']} |\n"
            continue
        md += (f"| {r['ticker']} | {r['fiscal_year']} | {'Y' if r['ocf_available'] else 'N'} | "
               f"{r['capex_before'] or '—'} | {r['capex_after'] or '—'} | "
               f"{'Y' if r['fcf_before'] else 'N'} | {'Y' if r['fcf_after'] else 'N'} | "
               f"{'YES' if r['unlocked_by_m11'] else ''} | {', '.join(r['missing_concepts']) or '—'} |\n")
    md += "\n> Capex chain (M11): " + ", ".join(f"`{c}`" for c in _CONCEPT_CHAINS["capex"]) + ".\n"
    md += "> Excluded by design: `PaymentsToAcquireBusinessesNetOfCashAcquired` (M&A, not capex), "
    md += "`CapitalExpendituresIncurredButNotYetPaid` (accrual disclosure, not a cash outflow).\n"
    with open(os.path.join(REPORTS_DIR, "fcf_coverage_audit.md"), "w") as fh:
        fh.write(md)

    # ── WACC summary report ──────────────────────────────────────────────
    wacc_payload = {"generated_at": now, "tickers": TICKERS, "rows": wacc_rows,
                    "defaults": {"risk_free_rate": 0.045, "equity_risk_premium": 0.05,
                                 "fallback_cost_of_debt": 0.05, "fallback_tax_rate": 0.21,
                                 "fallback_wacc": 0.10}}
    with open(os.path.join(REPORTS_DIR, "wacc_summary.json"), "w") as fh:
        json.dump(wacc_payload, fh, indent=2)

    def pct(x):
        return f"{x*100:.2f}%" if isinstance(x, (int, float)) else "—"

    md = "# Dynamic WACC Summary — Phase A (M11)\n\n"
    md += f"_Generated {now}._\n\n"
    md += "Phase A is deterministic (no FRED/FMP): risk-free 4.5%, ERP 5.0%, sector/theme "
    md += "beta fallback, cost of debt = interest/total debt (else 5%), effective tax = "
    md += "income tax/pretax (else 21%). Replaces the fixed 10% reverse-DCF discount rate.\n\n"
    md += "| Ticker | WACC | Beta (source) | Ke | Kd (source) | Tax (source) | w_e | Conf |\n"
    md += "|---|---|---|---|---|---|---|---|\n"
    for r in wacc_rows:
        bs = (r["beta_source"] or "").replace("sector_fallback:", "")
        md += (f"| {r['ticker']} | {pct(r['wacc'])} | {r['beta']} ({bs}) | {pct(r['cost_of_equity'])} | "
               f"{pct(r['cost_of_debt'])} ({(r['cost_of_debt_source'] or '').replace('interest_expense/total_debt','facts')}) | "
               f"{pct(r['tax_rate'])} ({(r['tax_rate_source'] or '').replace('income_tax/pretax','facts')}) | "
               f"{pct(r['weight_equity'])} | {r['confidence']} |\n")
    md += "\n> Confidence < 1.0 where cost of debt or tax fell back to defaults "
    md += "(e.g. ACRS: no interest expense, negative pretax income). Beta is a sector "
    md += "fallback in Phase A; Phase B will source live beta + FRED risk-free.\n"
    with open(os.path.join(REPORTS_DIR, "wacc_summary.md"), "w") as fh:
        fh.write(md)

    print(f"FCF coverage: {before_n}/{len(TICKERS)} → {after_n}/{len(TICKERS)}")
    print("Wrote reports/fcf_coverage_audit.{json,md} + reports/wacc_summary.{json,md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
