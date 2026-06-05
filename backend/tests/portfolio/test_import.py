import os
import sys
import csv
import tempfile
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from scripts.import_portfolio import import_portfolio, fetch_current_price, parse_money

def test_parse_money():
    assert parse_money("$1,234.56") == 1234.56
    assert parse_money(" 1 234.56 ") == 1234.56
    assert parse_money("100") == 100.0
    assert parse_money("") is None
    assert parse_money("invalid") is None

def test_fetch_current_price_success():
    with patch("scripts.import_portfolio.yf.Ticker") as mock_ticker:
        mock_stock = MagicMock()
        mock_history = MagicMock()
        mock_history.empty = False
        
        class MockSeries:
            @property
            def iloc(self):
                class MockILoc:
                    def __getitem__(self, key):
                        return 150.0
                return MockILoc()
        
        mock_history.__getitem__.return_value = MockSeries()
        mock_stock.history.return_value = mock_history
        mock_ticker.return_value = mock_stock

        price = fetch_current_price("AAPL")
        assert price == 150.0

def test_import_portfolio():
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        writer = csv.writer(tmp)
        writer.writerow(["ticker", "quantity", "average_cost", "current_price_optional", "current_value_optional", "asset_type", "notes"])
        writer.writerow(["AAPL", "10", "140.0", "150.0", "", "Stock", "Long term"])
        writer.writerow(["MSFT", "5", "200.0", "", "", "Stock", "Growth"])
        writer.writerow(["VOO", "", "", "", "500.00", "ETF", "Core"])
        csv_path = tmp.name

    try:
        with patch("scripts.import_portfolio.transaction") as mock_transaction, \
             patch("scripts.import_portfolio.fetch_current_price") as mock_fetch:
            
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            
            mock_transaction.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value = mock_cur

            mock_fetch.return_value = 250.0
            
            mock_cur.fetchone.return_value = (1,)

            import_portfolio(csv_path, "Test Portfolio")

            assert mock_conn.execute.call_count == 4
            
            first_call_args = mock_conn.execute.call_args_list[0][0]
            assert "INSERT INTO portfolios" in first_call_args[0]
            
            second_call_args = mock_conn.execute.call_args_list[1][0]
            assert "INSERT INTO portfolio_positions" in second_call_args[0]
            # AAPL: q=10, c=140, p=150 -> val=1500, src='quantity_x_current_price'
            assert second_call_args[1] == (1, "AAPL", 10.0, 140.0, 150.0, 1500.0, "quantity_x_current_price", "Stock", "Long term")

            third_call_args = mock_conn.execute.call_args_list[2][0]
            # MSFT: q=5, c=200, fetch=250 -> val=1250, src='quantity_x_current_price'
            assert third_call_args[1] == (1, "MSFT", 5.0, 200.0, 250.0, 1250.0, "quantity_x_current_price", "Stock", "Growth")

            fourth_call_args = mock_conn.execute.call_args_list[3][0]
            # VOO: q=None, c=None, val_opt=500.00 -> val=500.00, src='current_value_optional'
            assert fourth_call_args[1] == (1, "VOO", None, None, 250.0, 500.00, "current_value_optional", "ETF", "Core")
            
    finally:
        os.remove(csv_path)
