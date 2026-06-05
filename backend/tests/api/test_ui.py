from fastapi.testclient import TestClient
import json
import pytest
from app.main import app
from app.api.routes.ui import REPORTS_DIR

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_mock_reports(tmp_path, monkeypatch):
    # Use a temporary directory for reports
    monkeypatch.setattr("app.api.routes.ui.REPORTS_DIR", tmp_path)
    
    # Create some mock reports
    (tmp_path / "my_real_portfolio_report.json").write_text(json.dumps({"test": "portfolio"}))
    (tmp_path / "portfolio_coverage.json").write_text(json.dumps([{"ticker": "AAPL"}]))
    (tmp_path / "TEST_scorecard.json").write_text(json.dumps({"score": 10}))
    (tmp_path / "TEST_valuation_scorecard.json").write_text(json.dumps({"value": 100}))
    (tmp_path / "TEST_memo.md").write_text("# Test Memo")
    
    yield tmp_path

def test_list_reports():
    response = client.get("/api/reports")
    assert response.status_code == 200
    data = response.json()
    assert "reports" in data
    assert len(data["reports"]) == 5
    names = [r["name"] for r in data["reports"]]
    assert "my_real_portfolio_report.json" in names

def test_get_report_json():
    response = client.get("/api/reports/my_real_portfolio_report.json")
    assert response.status_code == 200
    assert response.json() == {"test": "portfolio"}

def test_get_report_md():
    response = client.get("/api/reports/TEST_memo.md")
    assert response.status_code == 200
    assert response.json() == {"content": "# Test Memo"}

def test_get_report_not_found():
    response = client.get("/api/reports/does_not_exist.json")
    assert response.status_code == 404

def test_get_latest_portfolio():
    response = client.get("/api/portfolio/latest")
    assert response.status_code == 200
    assert response.json() == {"test": "portfolio"}

def test_get_portfolio_coverage():
    response = client.get("/api/portfolio/coverage")
    assert response.status_code == 200
    assert response.json() == {"coverage": [{"ticker": "AAPL"}]}

def test_get_ticker_scorecard():
    response = client.get("/api/tickers/TEST/scorecard")
    assert response.status_code == 200
    assert response.json() == {"score": 10}

def test_get_ticker_valuation():
    response = client.get("/api/tickers/TEST/valuation")
    assert response.status_code == 200
    assert response.json() == {"value": 100}
