from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_live_portfolio_endpoint():
    res = client.get("/api/portfolio/live")
    assert res.status_code == 200
    data = res.json()
    assert "total_value" in data
    assert "daily_pnl" in data
    assert "holdings" in data
    
    if len(data["holdings"]) > 0:
        h = data["holdings"][0]
        assert "current_price" in h
        assert "daily_change_pct" in h
        assert "value_source" in h
