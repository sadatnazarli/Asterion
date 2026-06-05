"""Markdown rendering for decision-intelligence reports. Pure formatting."""
from __future__ import annotations

from app.decision_intelligence.schemas import (
    ComplianceSummary,
    DecisionReport,
    FinancialSummary,
)


def _findings_table(findings) -> list[str]:
    if not findings:
        return ["_No findings._", ""]
    rows = ["| Category | Level | Rationale |", "|---|---|---|"]
    for f in findings:
        rationale = (f.rationale or "").replace("|", "/")
        rows.append(f"| {f.category} | **{f.level}** | {rationale} |")
    rows.append("")
    return rows


def _financial_block(fin: FinancialSummary) -> list[str]:
    out = ["## Financial risk (Asterion)", "", fin.headline, ""]
    if not fin.available:
        out += ["> Asterion scorecard not found — financial risk not assessed.", ""]
        return out
    out += _findings_table(fin.findings)
    if fin.missing:
        out += [f"_Missing financial inputs:_ {', '.join(fin.missing)}", ""]
    return out


def _compliance_block(comp: ComplianceSummary) -> list[str]:
    out = ["## Compliance / entity risk (Verifex)", "",
           f"_Provider:_ **{comp.provider_status}** · _Match:_ **{comp.match_status}**",
           "", comp.headline, ""]
    out += _findings_table(comp.findings)
    if comp.matches:
        out += ["**Matches:**", ""]
        for m in comp.matches[:8]:
            cats = ", ".join(m.get("categories") or []) or "—"
            out.append(f"- {m.get('name')} · {cats} · {m.get('source') or 'verifex'}")
        out.append("")
    if comp.missing:
        out += [f"_Missing compliance inputs:_ {', '.join(comp.missing)}", ""]
    return out


def render_decision_md(r: DecisionReport) -> str:
    ident = r.ticker or "private"
    lines = [
        f"# Decision Intelligence — {r.entity_name}",
        "",
        f"**Entity:** {r.entity_name}  ·  **Ticker:** {ident}  ·  "
        f"**Type:** {'public' if r.is_public else 'private'}",
        "",
        f"**Combined classification:** `{r.classification}`",
        f"**Combined risk level:** `{r.combined_risk_level}`  ·  "
        f"**Confidence:** {r.confidence:.2f}",
        "",
        f"> {r.disclaimer}",
        "",
        "---",
        "",
    ]
    lines += _financial_block(r.financial_summary)
    lines += ["---", ""]
    lines += _compliance_block(r.compliance_summary)
    lines += ["---", "", "## Missing data", ""]
    lines += ([f"- {m}" for m in r.missing_data] or ["_None._"]) + [""]
    lines += ["## Evidence", ""]
    lines += ([f"- {e}" for e in r.evidence_links] or ["_None._"]) + [""]
    lines += ["## Recommended next research steps", ""]
    lines += ([f"- {s}" for s in r.recommended_next_research_steps] or ["_None._"]) + [""]
    lines += ["## What would change the conclusion", ""]
    lines += ([f"- {w}" for w in r.what_would_change_conclusion] or ["_None._"]) + [""]
    return "\n".join(lines)
