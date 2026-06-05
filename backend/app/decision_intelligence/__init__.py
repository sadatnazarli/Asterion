"""Decision-intelligence layer — merges Asterion financial risk with Verifex
compliance / entity risk into one evidence-backed view.

Hard rules (mirror Asterion's contract + the V1 integration plan, docs/30):
- No buy/sell language, ever. Outputs are research classifications only.
- Deterministic merge. No LLM arithmetic, no invented numbers.
- Missing data is shown as missing; a provider "no match" is NOT "clean".
- A sanctions / critical compliance hit forces ``blocked_by_compliance_signal``.
- Verifex is optional: a missing key or outage degrades to
  ``provider_unavailable`` and never breaks the report.
"""
