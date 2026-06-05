## M5: Scorecard & Deterministic Policy Engine

Asterion's M5 engine enforces a strict boundary between quantitative/qualitative analysis and the final investment decision. LLMs are explicitly barred from making "buy/sell" decisions or generating target prices. Instead, they produce structured red flags and thematic summaries which are passed to the deterministic policy engine.

### The Advanced Scorecard
The Scorecard evaluates 10 Asterion-specific models, but is governed by a strict data-dependency registry (`advanced_registry.py`).
- **P0 Models** (Current MVP): Uses existing SEC filings and financial ratios to calculate Operating Leverage Convexity, Reflexivity Risk, Misunderstood Change, Perception Shift, and Narrative Entropy.
- **Blocked Models**: Expectation gaps (Reverse DCF) and crowding risks are blocked from execution until external reliable price and flow data are introduced in later milestones. This completely prevents the system from inventing mathematically precise garbage.

### Deterministic Policy Engine
The Policy Engine evaluates the outputs of the Advanced Scorecard and the missing data reports to place the asset into a strict taxonomy of classifications.

**Allowed Classifications:**
- `strong_company_watchlist`
- `quality_compounder_candidate`
- `improving_business_candidate`
- `wait_for_valuation_data`
- `risk_review_required`
- `speculative_only`
- `avoid_due_to_red_flags`
- `insufficient_data`

If an asset has strong compounding traits but lacks external price data (which is currently the case), the engine will output `wait_for_valuation_data`. The engine is programmed to never emit a price target or guaranteed language.
