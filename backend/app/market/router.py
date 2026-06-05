from fastapi import APIRouter
import time
from .cache import MarketCache
from .finnhub_provider import FinnhubProvider
from .yfinance_provider import YFinanceProvider

router = APIRouter()
cache = MarketCache(quote_ttl=60, history_ttl=3600)
finnhub = FinnhubProvider()
yfinance = YFinanceProvider()

def fetch_quote(ticker: str):
    cached, timestamp = cache.quotes.get(ticker, (None, None))
    if cached and time.time() - timestamp < cache.quote_ttl:
        cached["cache_status"] = "hit"
        cached["cache_age"] = time.time() - timestamp
        return cached

    quote = finnhub.get_quote(ticker)
    if quote is not None:
        quote["provider_used"] = "finnhub"
    else:
        quote = yfinance.get_quote(ticker)
        if quote is not None:
            quote["provider_used"] = "yfinance"

    if quote:
        quote["cache_status"] = "miss"
        quote["cache_age"] = 0
        cache.set_quote(ticker, quote)
    return quote

def fetch_history(ticker: str, range_str: str):
    cached = cache.get_history(ticker, range_str)
    if cached:
        return cached

    hist = finnhub.get_history(ticker, range_str)
    if not hist:
        hist = yfinance.get_history(ticker, range_str)

    if hist:
        cache.set_history(ticker, range_str, hist)
    return hist

@router.get("/quote/{ticker}")
def get_quote(ticker: str, debug: bool = False):
    q = fetch_quote(ticker)
    if not q:
        return {"error": "Could not fetch quote"}
    
    if debug:
        return {
            "ticker": ticker,
            "price": q.get("c"),
            "change": q.get("d"),
            "change_percent": q.get("dp"),
            "provider_used": q.get("provider_used"),
            "fallback_chain": ["finnhub", "yfinance"],
            "cache_status": q.get("cache_status"),
            "cache_age": q.get("cache_age"),
            "last_updated": int(time.time()),
            "is_realtime_or_delayed": "delayed" if q.get("delayed") else "realtime",
            "raw_provider_timestamp": q.get("t")
        }
    return q

@router.get("/history/{ticker}")
def get_history(ticker: str, range: str = "1m"):
    h = fetch_history(ticker, range)
    return {"history": h}

@router.get("/sparkline/{ticker}")
def get_sparkline(ticker: str):
    h = fetch_history(ticker, "1m")
    if h:
        return {"sparkline": [x['c'] for x in h]}
    return {"sparkline": []}
