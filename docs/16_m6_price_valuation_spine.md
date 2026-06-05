## M6: Price and Valuation Spine

This milestone unlocks Asterion's ability to measure the expectations gap by ingesting reliable market price data, computing deterministic valuation multiples, and running a Reverse DCF model.

### 1. Robust Price Ingestion
Price ingestion is designed to be highly fault-tolerant so that broken 3rd-party APIs do not corrupt our deterministic SEC fact repository.
Asterion supports 3 layers of price ingestion in `prices.py`:
1. `yfinance`: Primary provider offering robust historical OHLCV.
2. `stooq`: A free, keyless HTTP CSV fallback.
3. `csv`: Local manual fallback for complete air-gapped or failure-mode runs.

### 2. Reverse DCF Logic
Instead of trying to predict the future to guess a target price (which is notoriously fragile), Asterion uses a **Reverse DCF**.
We take the current Enterprise Value and current FCF, apply a fixed WACC (10%) and Terminal Growth rate (2.5%), and *solve backwards* to find `g` (the implied 5-10 year cash flow growth rate).

This allows us to answer the question: *"What does the market expect this company to do to justify its current price?"*

### 3. The Expectations Gap Score
Once we know the market's implied growth rate (`g`), Asterion compares it against the company's historical fundamental trajectory (e.g., TTM revenue growth) and the qualitative RAG extractions (M4 memos). 
- If implied growth is 40%, but historic execution is 15%, the gap is wide (Dangerous).
- If implied growth is 8%, but historic execution is 25% and accelerating, the gap is negative (Mispriced upside).

### 4. Thesis Fragility Score
We run sensitivity perturbations against the Reverse DCF. If a 1% change in the discount rate destroys 45% of the implied value, the thesis is designated as Highly Fragile.

### 5. Policy Engine Updates
The deterministic policy engine no longer defaults to `wait_for_valuation_data` when price data is ingested. It now evaluates the EV/FCF, the Expectations Gap, and the Fragility scores to emit active, strictly-bounded classifications like `quality_compounder_candidate` or `wait_for_better_price`.
