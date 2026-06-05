import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from app.ingestion.prices import (
    get_price_provider,
    OHLCV,
    StooqProvider,
    YFinanceProvider,
    CSVProvider,
    FallbackProvider,
    PriceError
)

def test_get_price_provider():
    assert isinstance(get_price_provider("stooq"), StooqProvider)
    assert isinstance(get_price_provider("yfinance"), YFinanceProvider)
    assert isinstance(get_price_provider("csv"), CSVProvider)
    
    fallback = get_price_provider("fallback")
    assert isinstance(fallback, FallbackProvider)
    assert len(fallback.providers) == 3

    with pytest.raises(PriceError):
        get_price_provider("invalid")

@patch("yfinance.Ticker")
def test_yfinance_provider(mock_ticker):
    mock_df = MagicMock()
    mock_df.empty = False
    
    # Mock iterrows to yield a single row
    import pandas as pd
    idx = pd.Timestamp('2023-01-01')
    mock_row = pd.Series({
        "Open": 10.0,
        "High": 11.0,
        "Low": 9.0,
        "Close": 10.5,
        "Adj Close": 10.5,
        "Volume": 1000
    })
    mock_df.iterrows.return_value = [(idx, mock_row)]
    
    mock_t_instance = MagicMock()
    mock_t_instance.history.return_value = mock_df
    mock_ticker.return_value = mock_t_instance
    
    provider = YFinanceProvider()
    rows = provider.fetch_daily("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 10))
    
    assert len(rows) == 1
    assert rows[0].date == date(2023, 1, 1)
    assert rows[0].close == 10.5

@patch("app.ingestion.prices.os.path.exists")
def test_csv_provider(mock_exists, monkeypatch):
    mock_exists.return_value = True
    csv_data = "Date,Open,High,Low,Close,Volume\n2023-01-01,10.0,11.0,9.0,10.5,1000\n"
    
    import io
    monkeypatch.setattr("builtins.open", lambda f, mode, encoding="utf-8": io.StringIO(csv_data))
    
    provider = CSVProvider()
    rows = provider.fetch_daily("AAPL")
    
    assert len(rows) == 1
    assert rows[0].date == date(2023, 1, 1)
    assert rows[0].close == 10.5

def test_fallback_provider():
    p1 = MagicMock()
    p1.name = "p1"
    p1.fetch_daily.side_effect = PriceError("fail 1")
    
    p2 = MagicMock()
    p2.name = "p2"
    p2.fetch_daily.return_value = [OHLCV(date(2023, 1, 1), 10, 11, 9, 10, 10, 100)]
    
    fallback = FallbackProvider([p1, p2])
    rows = fallback.fetch_daily("AAPL")
    
    assert len(rows) == 1
    p1.fetch_daily.assert_called_once()
    p2.fetch_daily.assert_called_once()
