import requests
import time
from .provider_base import MarketProvider
from .provider_state import record_finnhub_success
from app.core.config import get_settings

class FinnhubProvider(MarketProvider):
    def __init__(self):
        self.base_url = "https://finnhub.io/api/v1"

    @property
    def api_key(self) -> str | None:
        return get_settings().finnhub_api_key

    def get_quote(self, ticker):
        if not self.api_key:
            return None
        try:
            res = requests.get(f"{self.base_url}/quote?symbol={ticker}&token={self.api_key}", timeout=5)
            if res.status_code == 200:
                data = res.json()
                current = data.get("c")
                if current is not None and current > 0:
                    record_finnhub_success()
                    return {
                        "c": current,
                        "d": data.get("d"),
                        "dp": data.get("dp"),
                        "t": data.get("t", int(time.time()))
                    }
        except Exception:
            pass
        return None

    def get_history(self, ticker, range_str):
        # Finnhub requires premium for some historical candles or uses different params
        # Fall back to yfinance for history
        return None
