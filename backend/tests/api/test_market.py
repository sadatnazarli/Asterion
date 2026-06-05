from fastapi.testclient import TestClient
from app.main import app
from app.market.cache import MarketCache

client = TestClient(app)

def test_market_quote_fallback():
    res = client.get("/api/market/quote/AAPL")
    assert res.status_code == 200
    data = res.json()
    assert "c" in data
    assert "t" in data

def test_market_quote_debug():
    res = client.get("/api/market/quote/AAPL?debug=true")
    assert res.status_code == 200
    data = res.json()
    assert "provider_used" in data
    assert "cache_status" in data
    assert "ticker" in data
    assert data["ticker"] == "AAPL"

def test_market_history():
    res = client.get("/api/market/history/AAPL?range=1d")
    assert res.status_code == 200
    data = res.json()
    assert "history" in data
    assert isinstance(data["history"], list)

def test_system_providers_masked():
    res = client.get("/api/system/providers")
    assert res.status_code == 200
    data = res.json()
    assert "finnhub" in data
    assert "fmp" in data
    
    # Check that keys are masked if configured
    for provider, info in data.items():
        if info.get("configured") and "masked_key" in info:
            key = info["masked_key"]
            if key:
                assert key.startswith("****")
                assert len(key) <= 8  # **** + 4 chars
