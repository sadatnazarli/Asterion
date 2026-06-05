# M8.5: Live Market Data and UI Redesign

## Overview
Asterion now features a live market data integration layer to enrich deterministic portfolio outputs with real-time pricing and interactive charting.

## Features
- **Live PNL Calculation:** The `/api/portfolio/live` endpoint calculates daily performance.
- **Provider Fallback:** Uses Finnhub as the primary quote provider (if `FINNHUB_API_KEY` is present), falling back to `yfinance`.
- **Caching Layer:** Quotes are cached for 60 seconds to prevent rate limits.
- **Charts:** Institutional-grade charting using `recharts` and `lightweight-charts`.

## Setup
To enable Finnhub for faster and more reliable live data:
1. Register for a free API key at finnhub.io
2. Start the backend with the environment variable:
   `FINNHUB_API_KEY=your_key_here fastapi dev app/main.py`
3. Asterion will automatically route quote requests through Finnhub.

## Limitations
- Free tier APIs may have rate limits or slight delays.
- "Cost Basis Missing" will be shown for portfolio rows where only `current_value_optional` was provided.
- Asterion does not perform live trading or portfolio execution.
