# M9 — Position Sizing Policy (Design)

**Status: DESIGN. Research-only output contract — no buy/sell.** This defines
risk-limit *bands* and a position-type taxonomy. Asterion never emits "buy",
"sell", "add", or "trim". It emits one of five **review states** per position so
the user can decide. This document also pins the exact status vocabulary the UI
and any future endpoint must use.

## Hard limits (deterministic, current values in `policy_rules.py`)

| Limit | Value | Rationale |
|---|---|---|
| Min core ETF exposure | **≥ 30%** | broad-market floor / ballast |
| Max single stock | **≤ 15%** | idiosyncratic blow-up cap |
| Max single theme | **≤ 25%** | correlated-cluster cap |
| Max speculative / biotech | **≤ 10%** | tail-risk sleeve cap |
| Max high-valuation-risk names (proposed) | **≤ 25%** aggregate | priced-for-perfection cap |
| Max AI / semiconductor (proposed) | **≤ 35%** aggregate | single-narrative cap |

The last two are **new proposals** (not yet enforced). They aggregate weight
across positions flagged `valuation_risk_watchlist` and across AI/semi themes.

## Position-type taxonomy

Each holding is tagged with exactly one type (today inferred from the `notes`
field; proposed: an explicit `position_type` column). Each type carries a
**suggested max weight band** — a band, not a target, and never a trade order.

| Type | Definition | Suggested max weight band |
|---|---|---|
| **core** | broad ETF (VOO/VTI-style) ballast | 30–60% (this is a *floor* too) |
| **compounder** | quality_compounder_candidate, durable margins/FCF | 5–12% each |
| **cyclical** | earnings swing with the cycle (semis, memory) | 4–8% each |
| **speculative** | pre-profit / biotch / binary outcome | 1–3% each, ≤10% aggregate |
| **research-only** | insufficient_data or needs valuation review | 0% until promoted |

## Output contract — the ONLY statuses Asterion may emit

No buy/sell. Per position, exactly one of:

| Status | Trigger |
|---|---|
| `within_risk_limit` | weight within all applicable bands/limits |
| `above_risk_limit` | weight exceeds a hard limit (single/theme/spec/val-risk/AI) |
| `under_review` | classification is risk_review_required / mixed signals |
| `needs_cost_basis` | no average_cost → can't assess lifetime P/L or sizing vs entry |
| `needs_valuation_review` | wait_for_valuation_data / valuation_risk_watchlist |

Portfolio-level it may additionally report which **hard limits are breached**
(e.g. "core ETF 18% — below 30% floor") — descriptive, not prescriptive.

## Mapping classification → status (deterministic)

```
insufficient_data            → under_review
wait_for_valuation_data      → needs_valuation_review
valuation_risk_watchlist     → needs_valuation_review
avoid_due_to_red_flags       → above_risk_limit   (if held) else under_review
quality_compounder_candidate → within_risk_limit  (subject to weight bands)
risk_review_required         → under_review
(missing average_cost)       → needs_cost_basis   (overrides, additive)
(weight > hard limit)        → above_risk_limit   (overrides)
```

Precedence: `above_risk_limit` > `needs_cost_basis` > `needs_valuation_review` >
`under_review` > `within_risk_limit`.

## Implementation note

Not built in M9. When implemented it lives in `app/portfolio/sizing.py` as pure
functions over the existing `positions` + scorecard data, reusing
`risk_metrics.py` weights and `policy_rules.py` limits. The risk page already
shows severity-graded cards; this taxonomy slots into those without UI redesign.
The five statuses above are the contract — any code or UI must use these exact
strings and must never substitute trade language.
