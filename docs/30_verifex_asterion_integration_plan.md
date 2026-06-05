# 30 — Verifex + Asterion Decision-Intelligence Integration (V1 Plan)

**Status:** V1, deterministic, intentionally small. No hype, no advice.
**Theme:** merge *financial risk* (Asterion) with *compliance / entity risk*
(Verifex) into one evidence-backed decision-intelligence view.

This document is the architecture contract. Code in `backend/app/decision_intelligence/`
and `backend/app/integrations/verifex/` implements a subset of it; everything
labelled *planned* is deliberately not built yet.

---

## 1. What Asterion provides

Asterion is the **financial** half. From its deterministic scorecards it already
answers, per company:

- Is this company financially strong? (profitability, balance-sheet signals)
- Is the valuation stretched? (EV/Revenue, P/S, reverse-DCF expectations)
- What growth is priced in? (expectations gap)
- What portfolio risk exists? (single-name / theme concentration)
- What data is missing? (every score carries a missing-data list + confidence)

Surfaces consumed by the integration:

- `reports/{TICKER}_valuation_scorecard.json` — public-company scorecard
  (`advanced_scores`, `metrics`, `classification`, `confidence`, `missing_data`).
- `reports/{TICKER}_IPO_scorecard.json` — IPO / private-company scorecard.

Asterion never issues buy/sell calls; the integration inherits that rule.

## 2. What Verifex provides

Verifex is the **compliance / entity** half. Given a legal entity name (or
identifier) it answers:

- Is this entity sanctioned?
- Is there PEP (politically-exposed-person) exposure?
- Are there watchlist hits?
- Are there regulatory / enforcement risks?
- Are there connected entities that create counterparty risk?
- (When available) adverse-media signals.

V1 treats Verifex as a single **entity-screen** call returning hits + a match
status. It is an **optional** provider: missing key/URL or an unreachable API
must never break Asterion.

## 3. What the combined system should answer

> "Before I spend research time on this entity, what is the *combined* risk —
> financial **and** compliance — and what is the evidence?"

One report, two evidence trails, a single combined classification, an explicit
confidence, and an explicit missing-data list. It recommends **next research
steps**, never a trade.

## 4. Data flow

```
                 ┌─────────────────────────────┐
   ticker /      │  generate_decision_report   │
   legal name ──▶│        (workflow)           │
                 └───────────────┬─────────────┘
            ┌────────────────────┼─────────────────────┐
            ▼                    ▼                     ▼
   Asterion scorecard    Verifex adapter        (no live market call)
   (file, deterministic) (HTTP, optional)
            │                    │
            │  FinancialSummary  │  ComplianceSummary
            └─────────┬──────────┴──────────┐
                      ▼                      │
              decision_intelligence.merger  │
                      │ combined risk model  │
                      ▼                      │
        DecisionReport (json + md) ──────────┘
                      │
                      ▼
        reports/decision_intelligence_{KEY}.json/md
                      │
                      ▼
        API /api/decision/{entity}  →  UI /decision/[entity]
```

Key properties: Asterion data is read from disk (deterministic, no network).
Verifex is the only network hop and is fully isolated — a failure there yields a
`provider_unavailable` compliance summary, and the report is still produced.

## 5. API contract

**Internal (Asterion API), implemented in V1:**

`GET /api/decision/{entity}` → the latest `decision_intelligence_{KEY}.json`, or
404 if none has been generated. `{entity}` is a ticker (`META`) or a slug
(`SPACEX`). Read-only; serves a file the workflow wrote.

**Verifex adapter contract (internal shape, V1):**

`VerifexClient.screen_entity(name, *, country=None) -> VerifexScreenResult`

```
VerifexScreenResult {
  status: "ok" | "no_match" | "provider_unavailable" | "error"
  query: str
  matches: [ VerifexMatch { name, match_score, categories[], country, source } ]
  raw: dict | None          # provider payload, never logged with secrets
  notes: str
}
```

- `status="provider_unavailable"` when key or base URL is missing, **or** the
  network call fails. Distinct from `no_match` (provider answered, found nothing).
- The HTTP base URL is **config-only**; no production URL is hardcoded.

**External Verifex HTTP contract:** *planned / unconfirmed.* Until the real
endpoint + schema are known, `client.py` ships the request/parse seam but makes
no live call unless `VERIFEX_API_BASE_URL` is set, and `mapper.py` maps a
documented, generic JSON shape. Re-map when the real schema lands.

## 6. Risk taxonomy

Single source of truth: `backend/app/decision_intelligence/risk_taxonomy.py`.

**Financial risk categories** (derived from Asterion scores):
`valuation_risk`, `profitability_risk`, `balance_sheet_risk`,
`thesis_fragility`, `expectations_gap`, `concentration_risk`.

**Compliance risk categories** (derived from Verifex hits):
`sanctions_risk`, `pep_risk`, `adverse_media_risk` (if available),
`watchlist_risk`, `regulatory_enforcement_risk`, `ownership_control_risk`,
`jurisdiction_risk`.

**Levels:** `none | low | medium | high | critical | unknown`
(`unknown` = data missing; never silently treated as `none`).

**Combined classification** (the only allowed outputs):
`clear_for_research`, `financial_risk_watchlist`, `compliance_risk_watchlist`,
`combined_risk_watchlist`, `insufficient_data`, `blocked_by_compliance_signal`.

Hard rule: a **sanctions** (or otherwise critical compliance) hit forces
`blocked_by_compliance_signal`, regardless of how clean the financials look.

## 7. What NOT to build yet

- No automated trading, scoring of trades, or buy/sell language. Ever.
- No live market-data call inside the decision workflow (read scorecards only).
- No batch/whole-universe screening — one entity per run in V1.
- No persistence DB table for decision reports — files only (like other reports).
- No real-time webhook ingestion from Verifex.
- No adverse-media NLP — pass through only what Verifex returns.
- No entity-resolution / fuzzy de-duplication beyond what Verifex returns.
- No caching layer for Verifex responses.
- No UI redesign; `/decision/[entity]` reuses existing components.

## 8. Security / privacy rules

- `VERIFEX_API_KEY` comes from **env only** (`config.settings`). Never hardcoded,
  never committed, never logged or printed (mask with `mask_api_key`).
- `.env` / `backend/.env` stay gitignored; `.env.example` ships empty keys.
- Verifex raw payloads may contain third-party personal data (PEP/sanctions).
  Decision reports written to `reports/` are **gitignored** (`/reports/`), like
  all generated reports. Demo/sample data must never include real screening hits.
- If the key is missing → `provider_unavailable`, not an error and not "clean".
- A Verifex outage must not block the app or other Asterion features.
- No Asterion personal/portfolio data is sent to Verifex — only the public entity
  name being screened.

## 9. MVP milestones

- **V1 (this):** config + adapter seam + combined risk model + workflow script +
  read-only API + minimal UI + tests. Verifex live calls gated behind a
  configured base URL; deterministic merge + evidence discipline throughout.
- **V1.1:** wire the real Verifex endpoint + response schema into `mapper.py`
  once known; record provider response metadata (request id, as-of).
- **V2:** entity resolution (ticker ↔ legal name ↔ Verifex id), connected-entity
  / counterparty graph, batch screening over a portfolio, response caching, and
  optional persistence. Still no advice.
