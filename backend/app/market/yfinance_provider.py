import yfinance as yf
import time
from .provider_base import MarketProvider

class YFinanceProvider(MarketProvider):
    def get_quote(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period="5d")
            if not history.empty:
                current_price = float(history["Close"].iloc[-1])
                prev_close = float(history["Close"].iloc[-2]) if len(history) > 1 else current_price
                change = current_price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0.0
                return {
                    "c": current_price,
                    "d": change,
                    "dp": change_pct,
                    "t": int(time.time()),
                    "delayed": True
                }
            return None
        except Exception:
            return None

    def get_history(self, ticker, range_str):
        period_map = {"1d": "1d", "5d": "5d", "1m": "1mo", "6m": "6mo", "1y": "1y", "5y": "5y"}
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period=period_map.get(range_str, "1mo"))
            if not history.empty:
                res = []
                for idx, row in history.iterrows():
                    res.append({
                        "t": int(idx.timestamp()),
                        "c": float(row["Close"])
                    })
                return res
            return []
        except Exception:
            return []
