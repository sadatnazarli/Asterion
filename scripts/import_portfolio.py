#!/usr/bin/env python3
import csv
import argparse
import psycopg
import os
import re
import yfinance as yf
from decimal import Decimal, InvalidOperation
from datetime import datetime

import sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
from app.db.session import transaction

def parse_money(value: str) -> float | None:
    if not value:
        return None
    # Remove $, spaces, and commas
    cleaned = re.sub(r'[$,\s]', '', value)
    try:
        return float(Decimal(cleaned))
    except InvalidOperation:
        return None

def fetch_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="1d")
        if not history.empty:
            return float(history["Close"].iloc[-1])
        return None
    except Exception as e:
        print(f"Failed to fetch price for {ticker}: {e}")
        return None

def import_portfolio(csv_path, portfolio_name, confirm_large_total=False):
    try:
        positions_to_insert = []
        total_value = 0.0

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get('ticker')
                if not ticker:
                    continue
                
                quantity = parse_money(row.get('quantity', ''))
                average_cost = parse_money(row.get('average_cost', ''))
                
                current_price_str = row.get('current_price_optional', '').strip()
                if current_price_str:
                    current_price = parse_money(current_price_str)
                else:
                    current_price = fetch_current_price(ticker)

                current_value_opt = parse_money(row.get('current_value_optional', ''))

                value_source = 'missing'
                current_value = None

                if current_value_opt is not None:
                    current_value = current_value_opt
                    value_source = 'current_value_optional'
                elif quantity is not None and current_price is not None:
                    current_value = quantity * current_price
                    value_source = 'quantity_x_current_price'
                elif quantity is not None and average_cost is not None:
                    current_value = quantity * average_cost
                    value_source = 'quantity_x_average_cost'

                # Sanity Checks
                if current_value is not None:
                    if current_value > 5000 and not confirm_large_total:
                        print(f"WARNING: Position {ticker} has a calculated value of ${current_value:,.2f} > $5,000. Verify the quantity column doesn't contain a dollar amount.")
                    
                    if value_source == 'quantity_x_current_price' and current_value_opt is not None:
                        calc_val = quantity * current_price
                        diff = abs(calc_val - current_value_opt) / max(current_value_opt, 1)
                        if diff > 0.05:
                            print(f"WARNING: Calculated value for {ticker} (${calc_val:,.2f}) differs from provided current_value_optional (${current_value_opt:,.2f}) by > 5%. Using current_value_optional.")
                            current_value = current_value_opt
                            value_source = 'current_value_optional'

                if quantity is not None and quantity > 100 and row.get('asset_type', '').lower() == 'stock':
                    print(f"WARNING: Quantity for {ticker} is {quantity} which is > 100. If this is a fractional portfolio, check if this is an invested dollar amount instead.")

                asset_type = row.get('asset_type')
                notes = row.get('notes')
                
                if current_value is not None:
                    total_value += current_value

                positions_to_insert.append((
                    ticker, quantity, average_cost, current_price, current_value, value_source, asset_type, notes
                ))

        if total_value > 10000 and not confirm_large_total:
            print(f"ERROR: Total portfolio value is ${total_value:,.2f} > $10,000. This is likely due to importing dollar amounts as share quantities. Run with --confirm-large-total to override.")
            return

        with transaction() as conn:
            cur = conn.execute("""
                INSERT INTO portfolios (name)
                VALUES (%s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id;
            """, (portfolio_name,))
            portfolio_id = cur.fetchone()[0]

            for pos in positions_to_insert:
                conn.execute("""
                    INSERT INTO portfolio_positions (portfolio_id, ticker, quantity, average_cost, current_price, current_value, value_source, asset_type, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (portfolio_id, ticker) DO UPDATE SET
                        quantity = EXCLUDED.quantity,
                        average_cost = EXCLUDED.average_cost,
                        current_price = EXCLUDED.current_price,
                        current_value = EXCLUDED.current_value,
                        value_source = EXCLUDED.value_source,
                        asset_type = EXCLUDED.asset_type,
                        notes = EXCLUDED.notes;
                """, (portfolio_id, *pos))

            print(f"Successfully imported portfolio '{portfolio_name}' from {csv_path}. Total value: ${total_value:,.2f}")
    except Exception as e:
        print(f"Error importing portfolio: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import portfolio from CSV")
    parser.add_argument("csv_path", help="Path to the portfolio CSV file")
    parser.add_argument("--name", default="My Portfolio", help="Name of the portfolio")
    parser.add_argument("--confirm-large-total", action="store_true", help="Override safety warning if portfolio > $10,000")
    args = parser.parse_args()

    import_portfolio(args.csv_path, args.name, args.confirm_large_total)
