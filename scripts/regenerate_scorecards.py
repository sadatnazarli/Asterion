"""M10: regenerate valuation scorecards from REAL per-ticker data and report the
variance vs the old mock-fed scores.

Steps:
  1. Capture OLD advanced scores from the existing reports/*.json.
  2. Regenerate each scorecard via app.scoring.scorecard_generator (real data).
  3. Write reports/advanced_score_variance.{md,json} (old vs new + cross-ticker variance).

Usage:
    .venv/bin/python ../scripts/regenerate_scorecards.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import psycopg  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.backtesting.dataset import load_price_history  # noqa: E402
from app.scoring.scorecard_generator import generate_real_scorecard  # noqa: E402

TICKERS = ["META", "NVDA", "MSFT", "MU", "VRT", "BLK", "PLTR", "ACRS", "V"]
SCORE_KEYS = [
    "operating_leverage_convexity", "reflexivity_risk", "expectations_gap",
    "thesis_fragility", "misunderstood_change",
]
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))


# The pre-M10 generator fed IDENTICAL mock constants to every ticker, so the old
# advanced scores were the same for all 9 names. Those values are deterministic
# and known (the original scorecard JSONs have since been overwritten with real
# data), so we use them as the documented baseline rather than re-reading files.
OLD_MOCK_BASELINE: dict[str, float | None] = {
    "operating_leverage_convexity": 70.25,  # 50 + 0.81*100*0.25 (mock GM & growth)
    "reflexivity_risk": 0.0,                 # mock current_ratio 5.5, dte 0.0
    "expectations_gap": 75.0,                # mock implied 0.25 vs historical 0.15
    "thesis_fragility": 80.0,                # mock dcf_sensitivity_impact 0.8
    "misunderstood_change": None,            # not emitted in pre-M10 scorecards
}


def read_old_scores(ticker: str) -> dict[str, float | None]:
    # Identical mock baseline for every ticker (see OLD_MOCK_BASELINE).
    return dict(OLD_MOCK_BASELINE)


def write_markdown_scorecard(ticker: str, sc: dict) -> None:
    md = f"# {ticker} Valuation Scorecard (M10 — real inputs)\n\n"
    md += f"**Date:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n\n"
    md += f"**Classification:** {sc.get('classification')}  ·  confidence {sc.get('confidence')}\n\n"
    md += f"**Reason:** {sc.get('reason')}\n\n"
    md += f"**Market cap:** {sc.get('market_cap')}  ·  price used {sc.get('price_used')}\n\n"
    md += f"**Input missing flags:** {', '.join(sc.get('input_missing_flags') or []) or 'none'}\n\n"
    md += "## Advanced scores (real)\n\n"
    for k, v in (sc.get("advanced_scores") or {}).items():
        md += f"### {k}\n- score: {v.get('score'):.1f}\n- confidence: {v.get('confidence'):.2f}\n"
        md += f"- missing: {', '.join(v.get('missing_inputs') or []) or 'none'}\n- {v.get('explanation')}\n\n"
    md += "## Real metrics used\n\n"
    for k, val in sorted((sc.get("real_inputs") or {}).items()):
        md += f"- {k}: {val}\n"
    md += "\n> Generated from SEC facts + reverse-DCF + price history. No mock constants.\n"
    path = os.path.join(REPORTS_DIR, f"{ticker}_valuation_scorecard.md")
    with open(path, "w") as f:
        f.write(md)


def main() -> int:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    old = {t: read_old_scores(t) for t in TICKERS}

    new_scores: dict[str, dict] = {}
    rows = []
    with psycopg.connect(settings.db_dsn_sync) as conn:
        for t in TICKERS:
            print(f"Regenerating {t} …")
            closes = [b.close for b in load_price_history(t, lookback_days=400)]
            sc = generate_real_scorecard(conn, t, price_history=closes or None)
            new_scores[t] = sc
            # write the real scorecard JSON + MD
            with open(os.path.join(REPORTS_DIR, f"{t}_valuation_scorecard.json"), "w") as f:
                json.dump(sc, f, indent=2)
            write_markdown_scorecard(t, sc)

            adv = sc.get("advanced_scores", {})
            for k in SCORE_KEYS:
                blk = adv.get(k, {})
                rows.append({
                    "ticker": t,
                    "score_key": k,
                    "old_score": old[t].get(k),
                    "new_score": blk.get("score"),
                    "confidence": blk.get("confidence"),
                    "missing_inputs": blk.get("missing_inputs", []),
                    "explanation": blk.get("explanation", ""),
                })

    # cross-ticker variance per score key (new vs old)
    variance = {}
    for k in SCORE_KEYS:
        new_vals = [r["new_score"] for r in rows if r["score_key"] == k and r["new_score"] is not None]
        old_vals = [o[k] for o in old.values() if o.get(k) is not None]
        variance[k] = {
            "new_min": min(new_vals) if new_vals else None,
            "new_max": max(new_vals) if new_vals else None,
            "new_stdev": round(statistics.pstdev(new_vals), 3) if len(new_vals) > 1 else 0.0,
            "new_distinct_values": len(set(round(v, 1) for v in new_vals)),
            "old_stdev": round(statistics.pstdev(old_vals), 3) if len(old_vals) > 1 else 0.0,
            "old_distinct_values": len(set(round(v, 1) for v in old_vals)) if old_vals else 0,
            "n": len(new_vals),
        }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tickers": TICKERS,
        "rows": rows,
        "variance_by_score": variance,
    }
    with open(os.path.join(REPORTS_DIR, "advanced_score_variance.json"), "w") as f:
        json.dump(payload, f, indent=2)

    # markdown
    md = "# Advanced Score Variance — Mock vs Real Inputs (M10)\n\n"
    md += f"_Generated {payload['generated_at']}._\n\n"
    md += "Before M10 every ticker shared identical mock inputs, so advanced scores "
    md += "were constant across the book. After wiring real SEC-facts + reverse-DCF + "
    md += "price-history inputs, scores vary per ticker.\n\n"
    md += "## Cross-ticker variance (stdev & distinct values)\n\n"
    md += "| Score | old stdev | old distinct | new stdev | new distinct | new min | new max |\n"
    md += "|---|---|---|---|---|---|---|\n"
    for k in SCORE_KEYS:
        v = variance[k]
        md += (f"| {k} | {v['old_stdev']} | {v['old_distinct_values']} | {v['new_stdev']} | "
               f"{v['new_distinct_values']} | "
               f"{v['new_min']:.1f} | {v['new_max']:.1f} |\n" if v['new_min'] is not None
               else f"| {k} | {v['old_stdev']} | {v['old_distinct_values']} | {v['new_stdev']} | {v['new_distinct_values']} | — | — |\n")
    md += "\n## Per-ticker, per-score (old → new)\n\n"
    md += "| Ticker | Score | Old | New | Conf | Missing |\n|---|---|---|---|---|---|\n"
    for r in rows:
        old_s = f"{r['old_score']:.1f}" if r["old_score"] is not None else "—"
        new_s = f"{r['new_score']:.1f}" if r["new_score"] is not None else "—"
        conf = f"{r['confidence']:.2f}" if r["confidence"] is not None else "—"
        miss = ", ".join(r["missing_inputs"]) or "—"
        md += f"| {r['ticker']} | {r['score_key']} | {old_s} | {new_s} | {conf} | {miss} |\n"
    md += "\n> Old scores were identical across tickers (mock constants). New scores "
    md += "are derived per ticker; a score still showing low confidence / missing flags "
    md += "reflects a genuine data gap (e.g. capex not in facts → no FCF → no reverse-DCF), not a fabricated value.\n"
    with open(os.path.join(REPORTS_DIR, "advanced_score_variance.md"), "w") as f:
        f.write(md)

    print(f"\nWrote reports/advanced_score_variance.json + .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
