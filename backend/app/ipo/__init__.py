"""IPO / private-company analysis mode (M13).

A self-contained, deterministic pipeline for analysing a company that is filing
to go public (e.g. SpaceX → SPCX) *before* it trades as a normal public ticker.

Hard rules (mirror Asterion's contract):
- Verify the filing from the official source (SEC EDGAR) first. Never assume IPO
  news is real.
- Never invent financials, share counts, prices, valuations, or dates. Every
  number carries provenance and a confidence; a missing input is shown as missing.
- No buy/sell recommendations. Output research-only classifications.
- When free cash flow is negative we do NOT run a normal reverse DCF — we use a
  scenario / revenue-multiple model and label it speculative.
"""
