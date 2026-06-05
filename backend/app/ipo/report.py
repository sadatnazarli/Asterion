"""Deterministic markdown rendering for IPO-mode reports. Pure (str -> str)."""
from __future__ import annotations

from app.ipo.schemas import IpoScorecard, VerificationResult


def render_verification_md(v: VerificationResult) -> str:
    lines = [
        "# SpaceX — IPO Source Verification",
        "",
        "> IPO / private company mode. Official-source check only. Not investment advice.",
        "",
        f"- **Query:** {v.query}",
        f"- **Official IPO filing found:** {'YES' if v.filing_found else 'NO'}",
        f"- **Registrant:** {v.registrant_name or '—'}",
        f"- **CIK:** {v.cik or '—'}",
        f"- **Proposed ticker:** {v.proposed_ticker or '—'}",
        "",
        "## Filings",
    ]
    if v.filings:
        lines.append("| Form | Filed | Accession | URL |")
        lines.append("|------|-------|-----------|-----|")
        for f in v.filings:
            lines.append(f"| {f.get('form')} | {f.get('filing_date')} | "
                         f"{f.get('accession')} | {f.get('url') or '—'} |")
    else:
        lines.append("_No official S-1 / F-1 / 424B IPO filing found._")
    lines += ["", "## Sources checked"]
    lines += [f"- {s}" for s in v.sources_checked]
    lines += ["", "## Notes"]
    lines += [f"- {n}" for n in v.notes]
    lines += ["", "## Not verified in this pass (require reading the filing body)",
              "- Proposed price range / final price", "- Total shares offered & resulting float",
              "- Implied valuation, use of proceeds, lock-up schedule",
              "- Underwriter syndicate, voting structure detail",
              "", "_Where the filing exists, these are extracted in the IPO scorecard._", ""]
    return "\n".join(lines)


def _fmt_m(v) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1e6:
        return f"${v/1e6:.2f}T"
    if abs(v) >= 1e3:
        return f"${v/1e3:.1f}B"
    return f"${v:,.0f}M"


def render_scorecard_md(sc: IpoScorecard) -> str:
    val = sc.valuation
    m = val.metrics
    lines = [
        f"# {sc.ticker} — IPO Valuation Scorecard",
        "",
        "> **IPO / private company mode — NOT a normal public ticker analysis.**",
        f"> {sc.disclaimer}",
        "",
        f"- **Classification:** `{sc.classification}`  (research-only — no buy/sell)",
        f"- **Confidence:** {sc.confidence:.2f}",
        f"- **Official filing verified:** {'YES' if sc.verification.filing_found else 'NO'} "
        f"(CIK {sc.verification.cik or '—'}, ticker {sc.verification.proposed_ticker or '—'})",
        "",
        "## Thesis",
        sc.thesis,
        "",
        "## Valuation",
    ]
    if val.can_value:
        lines += [
            f"- Implied market cap: {_fmt_m(m.get('implied_market_cap_musd'))}",
            f"- Enterprise value: {_fmt_m(m.get('enterprise_value_musd'))} "
            f"({'net-cash approx' if m.get('enterprise_value_musd') is not None else 'n/a'})",
            f"- EV / Revenue: {('%.0fx' % m['ev_to_revenue']) if m.get('ev_to_revenue') else '—'}",
            f"- Price / Sales: {('%.0fx' % m['price_to_sales']) if m.get('price_to_sales') else '—'}",
            f"- Operating margin: {('%.0f%%' % (m['operating_margin']*100)) if m.get('operating_margin') is not None else '—'}",
            f"- Offering dilution: {('%.1f%%' % (m['offering_dilution_pct']*100)) if m.get('offering_dilution_pct') is not None else '—'}",
            f"- Method: `{val.method}`",
        ]
    else:
        lines.append("_Valuation not computed — missing price and/or share count._")
    if val.scenarios:
        lines += ["", "### Path-to-FCF scenarios (SPECULATIVE — FCF negative/unconfirmed)",
                  "| Scenario | Rev CAGR | FCF margin | Term. mult | PV EV | Gap vs IPO EV |",
                  "|----------|---------|-----------|-----------|-------|---------------|"]
        for s in val.scenarios:
            gap = s.get("gap_vs_ipo_ev_pct")
            lines.append(f"| {s['scenario']} | {s['revenue_cagr']:.0%} | {s['target_fcf_margin']:.0%} "
                         f"| {s['terminal_fcf_multiple']:.0f}x | {_fmt_m(s['pv_enterprise_value_musd'])} "
                         f"| {('%+.0f%%' % (gap*100)) if gap is not None else '—'} |")
    if val.comps:
        lines += ["", "### Comps (context only — multiples approximate, verify live)",
                  "| Ticker | Quality | Ref EV/Sales | Note |", "|--------|---------|------------|------|"]
        for c in val.comps:
            lines.append(f"| {c['ticker']} | {c['quality']} | ~{c['ev_sales_ref']:.0f}x | {c['note']} |")

    lines += ["", "## Risks"]
    if sc.risks:
        lines.append("| Category | Level | Rationale |")
        lines.append("|----------|-------|-----------|")
        for r in sc.risks:
            lines.append(f"| {r.category} | **{r.level}** | {r.rationale} |")
    else:
        lines.append("_Risk engine not run (unverified mode)._")

    def bullets(title, items):
        return [f"\n## {title}"] + ([f"- {i}" for i in items] if items else ["- —"])

    lines += bullets("Missing data", sc.missing_data)
    lines += bullets("What must be verified before investing", sc.must_verify)
    lines += bullets("What would change the conclusion", sc.would_change_conclusion)
    lines += bullets("Suggested monitoring checklist", sc.monitoring_checklist)
    lines += ["", "---", "_Generated by Asterion IPO mode. Deterministic; every figure traces to the "
              "cited SEC filing. Research only — not financial advice, no buy/sell recommendation._", ""]
    return "\n".join(lines)
