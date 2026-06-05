"""IPO risk engine (Phase 6) + research-only classification (Phase 7). Pure.

Seven IPO-specific risk categories, scored deterministically from the verified
facts where numbers exist and held at a structural level (with rationale) where
the signal is qualitative. The classifier maps the evidence to ONE research-only
label — never buy/sell.
"""
from __future__ import annotations

from app.ipo.schemas import (
    FilingFacts,
    IpoScorecard,
    RiskFinding,
    ValuationResult,
    VerificationResult,
)

# Key facts that drive confidence — fraction present => coverage.
_KEY_FACTS = (
    "ipo_price_per_share", "shares_offered", "total_shares_pre_offering",
    "revenue_fy2025", "loss_from_operations_fy2025", "cash_and_equivalents",
    "class_b_votes_per_share", "lockup_days",
)


def assess_risks(facts: FilingFacts, val: ValuationResult) -> list[RiskFinding]:
    out: list[RiskFinding] = []
    ev_sales = val.metrics.get("ev_to_revenue") or val.metrics.get("price_to_sales")
    op_margin = val.metrics.get("operating_margin")

    # 1. Valuation risk
    if ev_sales is None:
        out.append(RiskFinding("valuation", "unknown",
                               "Valuation multiple not computable (missing price/shares/revenue).",
                               ["missing inputs"]))
    else:
        lvl = "high" if ev_sales >= 20 else "elevated" if ev_sales >= 8 else "moderate"
        out.append(RiskFinding("valuation", lvl,
                               f"EV/Revenue ~{ev_sales:.0f}x prices in years of compounding growth; "
                               f"little margin for error.",
                               [f"EV/Revenue ~{ev_sales:.1f}x", "vs aerospace primes ~2-3x"]))

    # 2. Profitability risk
    ev_pos = val.fcf_positive
    if op_margin is not None and op_margin < 0:
        out.append(RiskFinding("profitability", "high",
                               f"Negative operating margin ({op_margin:.0%}); FCF "
                               f"{'unconfirmed' if ev_pos is None else ('positive' if ev_pos else 'negative')}. "
                               f"Capex-intensive.",
                               ["loss from operations (FY)", "heavy capex (launch/Starlink/Starship)"]))
    else:
        out.append(RiskFinding("profitability", "elevated" if ev_pos is False else "moderate",
                               "Profitability/FCF mixed; capex intensity remains a swing factor.",
                               ["capex intensity"]))

    # 3. Governance risk — super-voting / founder control
    b_votes = facts.num("class_b_votes_per_share")
    if b_votes and b_votes >= 10:
        out.append(RiskFinding("governance", "high",
                               "Dual-class super-voting structure (Class B = 10 votes) concentrates "
                               "control with the founder; public Class A holders have limited say.",
                               ["Class B 10 votes/share", "founder controls majority of votes",
                                "related-party transactions to verify in filing"]))
    else:
        out.append(RiskFinding("governance", "unknown",
                               "Voting structure not parsed; verify control/related-party terms.",
                               ["voting structure missing"]))

    # 4. Lock-up / supply risk
    lk = facts.num("lockup_days")
    if lk:
        out.append(RiskFinding("lockup_supply", "elevated",
                               f"{int(lk)}-day lock-up; expiry can release large insider supply. "
                               f"Secondary/over-allotment supply risk.",
                               [f"{int(lk)}-day lock-up", "insider + secondary supply on expiry"]))
    else:
        out.append(RiskFinding("lockup_supply", "unknown", "Lock-up terms not parsed.",
                               ["lock-up missing"]))

    # 5. Business concentration risk (structural / qualitative)
    out.append(RiskFinding("business_concentration", "elevated",
                           "Revenue concentrated in Starlink connectivity + government/NASA/defense "
                           "launch contracts; customer and program concentration to verify in filing.",
                           ["Starlink dependence", "government/NASA/defense contracts",
                            "launch-cadence dependence"]))

    # 6. Execution risk (structural)
    out.append(RiskFinding("execution", "elevated",
                           "Growth thesis leans on Starship maturation, Starlink scaling, and heavy "
                           "capex execution against competitive and regulatory pressure.",
                           ["Starship development", "satellite deployment cadence", "capex execution"]))

    # 7. IPO hype risk (no prediction)
    out.append(RiskFinding("ipo_hype", "elevated",
                           "High-profile, high-retail-interest listing. First-day demand can detach "
                           "price from fundamentals; post-IPO drawdown risk after lock-ups. "
                           "Asterion makes no first-day prediction.",
                           ["high retail interest", "index-inclusion flows later",
                            "history of high-hype IPO volatility"]))
    return out


def _coverage(facts: FilingFacts) -> float:
    present = sum(1 for k in _KEY_FACTS if facts.get(k) is not None)
    return present / len(_KEY_FACTS)


def classify(
    verification: VerificationResult,
    facts: FilingFacts,
    val: ValuationResult,
    risks: list[RiskFinding],
    *,
    unverified_mode: bool = False,
) -> tuple[str, float]:
    """Map evidence -> one research-only classification + confidence (0..1)."""
    if unverified_mode or not verification.filing_found:
        # No verified official filing: never investable.
        cls = "not_verifiable_yet" if unverified_mode else "wait_for_official_filing"
        return cls, 0.15

    high = {r.category for r in risks if r.level == "high"}
    cov = _coverage(facts)

    if "valuation" in high:
        cls = "valuation_risk_watchlist"
    elif cov >= 0.6 and val.can_value:
        cls = "research_candidate"
    else:
        cls = "avoid_until_more_data"

    # Confidence: filing verified gives a floor; coverage + valuability lift it.
    confidence = round(min(0.85, 0.35 + 0.4 * cov + (0.1 if val.can_value else 0.0)), 2)
    return cls, confidence


def build_scorecard(
    ticker: str,
    verification: VerificationResult,
    facts: FilingFacts,
    val: ValuationResult,
    *,
    unverified_mode: bool = False,
) -> IpoScorecard:
    """Assemble the full Phase-7 IPO scorecard."""
    risks = assess_risks(facts, val) if not unverified_mode else []
    cls, conf = classify(verification, facts, val, risks, unverified_mode=unverified_mode)

    key_risks = [f"{r.category}: {r.level}" for r in risks if r.level in ("high", "elevated")]
    missing = sorted(set(facts.missing) | set(val.missing))

    if unverified_mode:
        thesis = (f"{ticker}: IPO discussed in unverified news. No official SEC filing was "
                  f"confirmed in this run. Summarizing only what is unverified; no valuation "
                  f"score, not investable, not added to portfolio.")
    elif not verification.filing_found:
        thesis = (f"{ticker}: no official SEC S-1/F-1/424B filing found. Wait for an official "
                  f"filing before any analysis.")
    else:
        ev_sales = val.metrics.get("ev_to_revenue") or val.metrics.get("price_to_sales")
        mc = val.metrics.get("implied_market_cap_musd")
        thesis = (
            f"{ticker}: official S-1 verified on SEC EDGAR. At the expected IPO price the implied "
            f"market cap is ~${(mc or 0)/1e6:.2f}T on ~${facts.num('revenue_fy2025') or 0/1:.0f}M "
            f"FY revenue (EV/Revenue ~{ev_sales:.0f}x), with negative operating income and a "
            f"founder-controlled dual-class structure. The price embeds years of flawless "
            f"execution. Research-only: a valuation-risk watch item, not a recommendation."
        ) if ev_sales else (
            f"{ticker}: official S-1 verified, but key valuation inputs are missing — "
            f"cannot size the multiple. Avoid until more data."
        )

    must_verify = [
        "GAAP net income/loss and segment revenue (Starlink vs launch vs government)",
        "Operating cash flow and total capex -> true free cash flow sign",
        "Total debt and full capitalization table",
        "Final IPO price, shares sold, over-allotment, and resulting float",
        "Customer concentration and related-party transactions",
        "Exact lock-up schedule and timed-release provisions",
    ]
    would_change = [
        "A confirmed positive and growing FCF would shift from scenario model to a reverse DCF",
        "A materially lower final price / valuation would reduce valuation risk",
        "Disclosed segment economics could strengthen or weaken the concentration view",
        "Removal/sunset of super-voting would lower governance risk",
    ]
    monitoring = [
        "Final pricing vs the $135 expectation and first-day trading range",
        "First public earnings: revenue mix, margin trajectory, FCF",
        "Lock-up expiry dates and insider selling",
        "Starship / Starlink execution milestones",
        "Index-inclusion timing and resulting flows",
    ]

    return IpoScorecard(
        ticker=ticker.upper(),
        classification=cls,
        confidence=conf,
        thesis=thesis,
        verification=verification,
        facts=facts,
        valuation=val,
        risks=risks,
        key_risks=key_risks,
        missing_data=missing,
        must_verify=must_verify,
        would_change_conclusion=would_change,
        monitoring_checklist=monitoring,
    )
