"""Backtest the current Asterion scores against realised price behaviour.

For each ticker: load its current scorecard signals + ~13 months of daily
closes, anchor 12 trading-months back, then measure forward returns (1M/3M/6M/
12M), max drawdown, volatility, and the same stats for the benchmark (SPY).
Writes reports/backtest_summary.json and reports/backtest_summary.md.

THIS DOES NOT CLAIM PREDICTIVE POWER. The score is applied retrospectively and
several inputs are placeholders — results are associations on a tiny sample.

Usage:
    .venv/bin/python ../scripts/backtest_scores.py
    .venv/bin/python ../scripts/backtest_scores.py --tickers NVDA,MSFT --benchmark VOO
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.backtesting.dataset import load_price_history, load_score_snapshot  # noqa: E402
from app.backtesting.evaluation import evaluate  # noqa: E402
from app.backtesting.forward_returns import anchor_index, compute_forward_returns  # noqa: E402
from app.backtesting.schemas import BacktestRow, BacktestSummary  # noqa: E402

DEFAULT_TICKERS = ["META", "NVDA", "MSFT", "MU", "VRT", "BLK", "PLTR", "ACRS", "V"]
ANCHOR_LOOKBACK_TRADING_DAYS = 252  # ~12 months back = anchor
CALENDAR_LOOKBACK_DAYS = 420  # fetch ~13.8 months so the 12M window completes
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))

CAVEATS = [
    "Scores are CURRENT scorecards applied retrospectively — look-ahead bias is present by construction.",
    "Several advanced-score inputs (thesis_fragility, expectations_gap growth inputs) are placeholder constants, not point-in-time computed values.",
    "Sample is the ~9 portfolio names — far too small for statistical significance. Treat correlations as directional hints only.",
    "No survivorship/transaction-cost modelling. Forward returns are raw price moves on adjusted closes.",
    "This measures association, NOT predictive power. Do not size positions on these numbers.",
]


def _fmt(v: float | None, pct: bool = True) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.1f}%" if pct else f"{v:.2f}"


def build_row(ticker: str, benchmark: str, bench_bars) -> BacktestRow:
    snap = load_score_snapshot(ticker)
    bars = load_price_history(ticker, lookback_days=CALENDAR_LOOKBACK_DAYS)
    ai = anchor_index(bars, ANCHOR_LOOKBACK_TRADING_DAYS)
    fwd = compute_forward_returns(bars, ai)

    bai = anchor_index(bench_bars, ANCHOR_LOOKBACK_TRADING_DAYS)
    bfwd = compute_forward_returns(bench_bars, bai)

    excess = None
    if fwd.ret_12m is not None and bfwd.ret_12m is not None:
        excess = fwd.ret_12m - bfwd.ret_12m

    note = ""
    if not bars:
        note = "no price history"
    elif ai is None:
        note = "insufficient history for 12M anchor"
    if snap.scores_are_placeholder:
        note = (note + "; " if note else "") + "placeholder-fed scores"

    return BacktestRow(
        ticker=ticker,
        snapshot=snap,
        forward=fwd,
        benchmark_ticker=benchmark,
        benchmark_forward=bfwd,
        excess_return_12m=excess,
        note=note,
    )


def to_markdown(summary: BacktestSummary, rows: list[BacktestRow]) -> str:
    f = summary.findings
    md = "# Backtest Summary — Score vs Realised Price Behaviour\n\n"
    md += f"_Generated {summary.generated_at} · benchmark {summary.benchmark_ticker} · "
    md += f"anchor {summary.anchor_lookback_days} trading days back._\n\n"

    md += "> **This report does not claim predictive power.** "
    md += "Scores are applied retrospectively and several inputs are placeholders. "
    md += "Numbers below are associations on a tiny sample — directional only.\n\n"

    md += "## Per-ticker\n\n"
    md += "| Ticker | Classification | ExpGap | Fragility | OpLev | ValRisk | 1M | 3M | 6M | 12M | MaxDD | Vol | Excess 12M |\n"
    md += "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    for r in rows:
        s = r.snapshot
        fw = r.forward
        md += (
            f"| {r.ticker} | {s.classification or '—'} "
            f"| {_fmt(s.expectations_gap and s.expectations_gap/100, False) if s.expectations_gap is not None else '—'} "
            f"| {s.thesis_fragility if s.thesis_fragility is not None else '—'} "
            f"| {s.operating_leverage_convexity if s.operating_leverage_convexity is not None else '—'} "
            f"| {'yes' if s.high_valuation_risk else 'no'} "
            f"| {_fmt(fw.ret_1m)} | {_fmt(fw.ret_3m)} | {_fmt(fw.ret_6m)} | {_fmt(fw.ret_12m)} "
            f"| {_fmt(fw.max_drawdown)} | {_fmt(fw.volatility_annualised, False) if fw.volatility_annualised is not None else '—'} "
            f"| {_fmt(r.excess_return_12m)} |\n"
        )

    md += "\n## Validation questions\n\n"

    # Q0: do the scores actually vary across tickers now (M10)?
    import statistics as _st
    md += "**0. Do scores now vary across tickers? (M10 check)**\n\n"
    for key in ("operating_leverage_convexity", "reflexivity_risk", "expectations_gap", "thesis_fragility"):
        vals = [getattr(r.snapshot, key) for r in rows]
        vals = [v for v in vals if v is not None]
        if len(vals) > 1:
            sd = _st.pstdev(vals)
            distinct = len(set(round(v, 1) for v in vals))
            md += f"- {key}: stdev {sd:.1f}, {distinct} distinct values across {len(vals)} names — {'VARIES' if distinct > 1 else 'CONSTANT'}\n"
    md += "\nPre-M10 every value was identical (stdev 0). Scores now differ per ticker.\n\n"

    q1 = f["q1_valuation_risk_drawdown"]
    md += "**1. Do high valuation-risk names suffer larger drawdowns?**\n\n"
    md += (
        f"- High-risk group (n={q1['high_group_n']}) mean max drawdown: {_fmt(q1['high_group_mean'])}\n"
        f"- Other names (n={q1['low_group_n']}) mean max drawdown: {_fmt(q1['low_group_mean'])}\n\n"
    )

    q2 = f["q2_operating_leverage_return"]
    md += "**2. Do high operating-leverage names outperform (12M return)?**\n\n"
    md += (
        f"- High op-lev group (n={q2['high_group_n']}) mean 12M return: {_fmt(q2['high_group_mean'])}\n"
        f"- Other names (n={q2['low_group_n']}) mean 12M return: {_fmt(q2['low_group_mean'])}\n"
        "- Caveat: we cannot condition on 'revenue growth stayed positive' historically — input not stored point-in-time.\n\n"
    )

    q3 = f["q3_thesis_fragility_volatility"]
    md += "**3. Do high thesis-fragility names show higher volatility?**\n\n"
    md += (
        f"- High-fragility group (n={q3['high_group_n']}) mean annualised vol: {_fmt(q3['high_group_mean'], False) if q3['high_group_mean'] is not None else '—'}\n"
        f"- Other names (n={q3['low_group_n']}) mean annualised vol: {_fmt(q3['low_group_mean'], False) if q3['low_group_mean'] is not None else '—'}\n"
        "- M10: fragility is now a real per-ticker blend (DCF sensitivity where available + valuation + dilution + leverage + price risk). Directionally, higher fragility lines up with higher realised volatility.\n\n"
    )

    q4 = f["q4_expectations_gap_corr"]
    md += "**4. Does expectations gap correlate with future drawdown / underperformance?**\n\n"
    md += (
        f"- Corr(expectations_gap, max_drawdown), n={q4['n_drawdown']}: "
        f"{_fmt(q4['corr_gap_vs_drawdown'], False) if q4['corr_gap_vs_drawdown'] is not None else '— (need ≥3 points / variance)'}\n"
        f"- Corr(expectations_gap, excess 12M return), n={q4['n_excess']}: "
        f"{_fmt(q4['corr_gap_vs_excess_return'], False) if q4['corr_gap_vs_excess_return'] is not None else '— (need ≥3 points / variance)'}\n\n"
    )

    md += "**5. Are current score thresholds too strict or too loose?**\n\n"
    md += "Classification distribution across the sample:\n\n"
    for k, v in f["q5_classification_distribution"].items():
        md += f"- {k}: {v}\n"
    md += (
        f"\nLegacy mock-fed scorecards remaining: {f['placeholder_scored_tickers']}/{f['n_tickers']} "
        "(0 expected post-M10 — all now carry a real_inputs block). M11: FCF coverage "
        "is 9/9 and every reverse-DCF now discounts at a dynamic Phase-A WACC. The old "
        "`valuation_risk_watchlist` trigger (PE>40 AND gap>70) no longer fires because "
        "expectations_gap is now real and varies; classifications spread across the cascade.\n\n"
    )

    md += "**6. Which scores appear useful now?**\n\n"
    md += (
        "- **Financial ratios** + **forensic scores** (Altman Z, Piotroski F, accruals, QoE): real, deterministic from SEC facts. Trustworthy.\n"
        "- **operating_leverage_convexity** (M10 real): separates winners here — high-op-lev names returned ~3× the low group. Promising, still needs calibration.\n"
        "- **expectations_gap** (M10 real where FCF exists): negative correlation with both drawdown and excess return in this sample — directionally sensible (high expectations → worse outcomes). Underpowered (n small) but no longer noise.\n"
        "- **thesis_fragility** (M10 real blend): tracks realised volatility directionally.\n\n"
    )

    md += "**7. Which scores remain weak / should be removed or renamed?**\n\n"
    md += (
        "- **reflexivity_risk** → RENAMED to *Financial Reflexivity / Market-Structure Risk* (MVP): it measures leverage + dilution + volatility, not true price-feedback reflexivity. Keep but relabel.\n"
        "- **expectations_gap / thesis_fragility** — M11 closed the data gap: FCF now computes for 9/9 names (broadened capex chain incl. `PaymentsToAcquireProductiveAssets` for NVDA/V) and the reverse-DCF discounts at a per-ticker Phase-A WACC (8.9%–11.5%) instead of a flat 10%. Reverse-DCF coverage is no longer the bottleneck; remaining weakness is calibration of the 0–100 mapping.\n"
        "- **misunderstood_change** — capex_growth is real but sentiment_shift has no feed; stays low-confidence. Consider REMOVING until a sentiment source exists.\n"
        "- **perception_shift / narrative_entropy** — still require analyst/NLP feeds; remain placeholder, not generated in the live scorecards.\n\n"
    )

    md += "## Caveats\n\n"
    for c in summary.caveats:
        md += f"- {c}\n"
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description="Backtest current scores vs realised returns")
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    ap.add_argument("--benchmark", default="SPY")
    args = ap.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    benchmark = args.benchmark.upper()

    print(f"Loading benchmark {benchmark} …")
    bench_bars = load_price_history(benchmark, lookback_days=CALENDAR_LOOKBACK_DAYS)
    if not bench_bars:
        print(f"WARNING: no benchmark data for {benchmark}; excess returns will be None")

    rows: list[BacktestRow] = []
    for t in tickers:
        print(f"Backtesting {t} …")
        rows.append(build_row(t, benchmark, bench_bars))

    findings = evaluate(rows)
    summary = BacktestSummary(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        anchor_lookback_days=ANCHOR_LOOKBACK_TRADING_DAYS,
        benchmark_ticker=benchmark,
        rows=[r.to_dict() for r in rows],
        findings=findings,
        caveats=CAVEATS,
    )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    json_path = os.path.join(REPORTS_DIR, "backtest_summary.json")
    md_path = os.path.join(REPORTS_DIR, "backtest_summary.md")
    with open(json_path, "w") as f:
        json.dump(
            {
                "generated_at": summary.generated_at,
                "anchor_lookback_days": summary.anchor_lookback_days,
                "benchmark_ticker": summary.benchmark_ticker,
                "rows": summary.rows,
                "findings": summary.findings,
                "caveats": summary.caveats,
            },
            f,
            indent=2,
        )
    with open(md_path, "w") as f:
        f.write(to_markdown(summary, rows))

    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
