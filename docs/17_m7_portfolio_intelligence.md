## M7: Portfolio Intelligence Engine

This milestone transforms Asterion into a Portfolio Intelligence Engine. It enables importing a real-world portfolio and computing concentration, exposure risks, and valuation risks at the aggregate level.

### 1. Portfolio Data Layer
Asterion uses PostgreSQL to store portfolios, positions, and snapshot states:
- `portfolios`: Tracks distinct portfolios.
- `portfolio_positions`: Tracks tickers, quantities, and cost basis.
- `portfolio_snapshots`: A historical record of the total portfolio value and cash balance.
- `portfolio_risk_metrics`: Stores deterministic point-in-time risk outputs.

### 2. Portfolio Risk Metrics
Asterion calculates exact weights for every position and flags structural imbalances:
- **Single-Stock Concentration**: Flags if any single position (like PLTR or NVDA) exceeds 15% of the portfolio.
- **Theme/Sector Exposure**: Groups assets by type and notes, checking if speculative themes (like AI/semiconductors or biotech) exceed 25%.
- **Core Allocation**: Enforces a minimum structural baseline (e.g., 30%) in Core ETFs to dampen volatility.
- **Unrealized P/L**: Calculated deterministically based on average cost and current price.

### 3. Policy Engine Integration
The core value of Asterion is merging fundamental valuation with portfolio sizing.
Asterion checks if a position has an existing M6 Valuation Scorecard.
- If the ticker's classification is `VALUATION RISK WATCHLIST` (e.g., highly stretched multiples) AND the portfolio weight is high, Asterion produces a compound risk warning.
- Asterion does *not* generate "sell" recommendations, but rather highlights the structural fragility (e.g., "Warning: 18% of portfolio is in PLTR, which currently has a Valuation Risk Watchlist classification due to high expectations gaps. Vulnerable to multiple compression.").

### 4. Import & Generation
- Use `scripts/import_portfolio.py <file.csv>` to ingest holdings. If `current_price` is omitted from the CSV, Asterion fetches it from `yfinance`.
- Use `scripts/generate_portfolio_report.py` to generate the risk breakdown in Markdown and JSON.
