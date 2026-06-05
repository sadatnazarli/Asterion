"""The 16 Asterion scores — declarative registry (the contract).

Each score is 0-100, sector-relative (Z -> CDF) normalized, with stored raw
inputs, formula version, confidence, and a missing-data penalty. This module
declares *what* each score is and its report-specified inputs/weights; the actual
deterministic computation lives in ``app.scoring.builders`` (milestone M2) and
calls pure functions in ``app.quant``. No LLM ever computes these.

Walled garden: ``final_investment`` (#15) is regime-aware; ``final_trading`` (#16)
is strictly separate and experimental.

See docs/00_..._requirements.md §5 for the source weighting table.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FORMULA_BUNDLE_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class ScoreSpec:
    key: str
    title: str
    inputs: tuple[str, ...]
    weighting: str               # human-readable report formula (computed in Python)
    sector_relative: bool = True
    walled_trading: bool = False
    regime_aware: bool = False
    notes: str = ""
    sector_overrides: dict[str, str] = field(default_factory=dict)


SCORES: tuple[ScoreSpec, ...] = (
    ScoreSpec("fundamental_quality", "Fundamental Quality",
              ("piotroski_f", "dupont_roe", "roic", "fcf_conversion", "operating_margin"),
              "0.40*Z(ROIC-WACC) + 0.30*Z(FCF_Conv) + 0.20*(Piotroski/9) + 0.10*Z(OpMargin)",
              sector_overrides={"financials": "use ROE not ROIC", "utilities": "use ROE not ROIC"}),
    ScoreSpec("valuation_attractiveness", "Valuation Attractiveness",
              ("dcf_margin", "epv_margin", "fcf_yield", "ev_ebitda_premium"),
              "0.40*Z(DCF_margin) + 0.30*Z(EPV_margin) + 0.20*Z(FCF_yield) - 0.10*Z(EV/EBITDA_premium)",
              notes="Reverse-DCF implied growth > WACC => hard-cap score at 20.",
              sector_overrides={"reits": "use P/AFFO not EV/EBITDA"}),
    ScoreSpec("growth_durability", "Growth Durability",
              ("revenue_cagr_3y", "gross_profit_cagr_3y", "revenue_growth_variance", "rule_of_40"),
              "0.50*Z(Rev_CAGR) + 0.30*Z(GrossProfit_CAGR) - 0.20*sigma(RevGrowth)",
              sector_overrides={"saas": "route through Rule of 40"}),
    ScoreSpec("balance_sheet_safety", "Balance Sheet Safety",
              ("altman_z", "interest_coverage", "net_debt_ebitda", "current_ratio"),
              "0.50*Z(Altman) + 0.30*Z(InterestCov) - 0.20*Z(NetDebt/EBITDA)",
              sector_overrides={"services": "use Altman Z'' weights"}),
    ScoreSpec("profitability", "Profitability",
              ("croa", "operating_margin", "gross_profit_to_assets"),
              "0.40*Z(CROA) + 0.30*Z(OpMargin) + 0.30*Z(GrossProfit/Assets)",
              notes="Heavily penalize if operating cash flow unavailable."),
    ScoreSpec("momentum", "Momentum",
              ("return_12m", "return_1m", "daily_vol"),
              "CDF((Ret12m - Ret1m) / (sigma*sqrt(252)))"),
    ScoreSpec("technical_setup", "Technical Setup",
              ("vwap_distance", "bollinger_width", "rsi", "macd_hist", "poc_distance"),
              "reward VWAP proximity in vol-compression with bullish MACD divergence"),
    ScoreSpec("catalyst", "Catalyst",
              ("days_to_earnings", "pdufa_dates", "macro_calendar", "hist_iv_crush"),
              "(1/Days_remaining) * EventImportance(0.1..1.0)"),
    ScoreSpec("sentiment", "Sentiment",
              ("transcript_polarity", "risk_factor_expansion", "news_credibility"),
              "0.50*TranscriptPolarity - 0.50*RiskFactorExpansionPenalty",
              notes="Low weight by design; always cite extracted sentences."),
    ScoreSpec("risk", "Risk",
              ("beta_36m", "vol_90d", "market_correlation"),
              "inverted: higher score = greater stability"),
    ScoreSpec("downside_risk", "Downside Risk",
              ("sortino", "max_drawdown_3y", "cvar_95"),
              "0.40*Z(Sortino) - 0.40*Z(MaxDD) - 0.20*Z(CVaR)"),
    ScoreSpec("dilution_risk", "Dilution Risk",
              ("share_cagr_3y", "sbc_to_ocf"),
              "inverted; AUTO-FAIL (<10) if SBC > 40% of operating cash flow"),
    ScoreSpec("macro_sensitivity", "Macro Sensitivity",
              ("beta_dxy", "beta_10y", "beta_wti"),
              "normalized |regression betas| to DXY, 10Y yield, WTI"),
    ScoreSpec("insider_institutional", "Insider/Institutional Confidence",
              ("net_insider_buys_ex_10b5_1", "inst_13f_delta"),
              "0.60*Z(InsiderNetPurchases) + 0.40*Z(13F_delta)"),
    ScoreSpec("final_investment", "Final Investment Score",
              ("scores_1_to_14", "regime"),
              "regime-weighted ensemble of scores 1-14 (HMM/rules state)",
              regime_aware=True,
              notes="Heuristic ranking until Brier-calibrated; NOT a literal probability."),
    ScoreSpec("final_trading", "Final Trading Setup Score",
              ("premarket_gap_pct", "rvol", "float", "short_interest"),
              "penalize high spread / low RVOL; reward gap-and-go with high RVOL",
              sector_relative=False, walled_trading=True,
              notes="Experimental, paper-only, capital-capped. Walled off from investing."),
)

SCORES_BY_KEY: dict[str, ScoreSpec] = {s.key: s for s in SCORES}

assert len(SCORES) == 16, "Asterion defines exactly 16 scores."
