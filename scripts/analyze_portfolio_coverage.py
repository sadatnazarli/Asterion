#!/usr/bin/env python3
import argparse
import sys
import os
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db.session import transaction

def analyze_coverage(portfolio_name: str, reports_dir: str):
    reports_path = Path(reports_dir)
    reports_path.mkdir(exist_ok=True, parents=True)

    with transaction() as conn:
        # Get portfolio positions
        res = conn.execute("""
            SELECT ticker, quantity, average_cost, current_price, current_value, asset_type, notes
            FROM portfolio_positions pp
            JOIN portfolios p ON pp.portfolio_id = p.id
            WHERE p.name = %s
        """, (portfolio_name,))
        positions = res.fetchall()

        if not positions:
            print(f"No positions found for portfolio: {portfolio_name}")
            return

        coverage_data = []

        for row in positions:
            ticker, qty, avg_cost, curr_price, curr_val, asset_type, notes = row
            
            # Defaults
            has_price = curr_price is not None
            has_cik = False
            has_facts = False
            has_ratios = False
            has_rag = False
            has_memo = (reports_path / f"{ticker}_company_memo.md").exists()
            has_valuation = (reports_path / f"{ticker}_valuation_scorecard.md").exists()
            
            # Check DB mappings
            c_res = conn.execute("""
                SELECT c.id, c.cik 
                FROM companies c 
                JOIN tickers t ON t.company_id = c.id 
                WHERE t.symbol = %s
            """, (ticker,)).fetchone()
            
            if c_res:
                company_id, cik = c_res
                has_cik = bool(cik)
                
                # Check facts
                f_count = conn.execute("SELECT count(*) FROM financial_facts WHERE company_id=%s", (company_id,)).fetchone()[0]
                has_facts = f_count > 0
                
                # Check ratios
                r_count = conn.execute("SELECT count(*) FROM financial_ratios WHERE company_id=%s", (company_id,)).fetchone()[0]
                has_ratios = r_count > 0
                
                # Check RAG chunks
                rag_count = conn.execute("""
                    SELECT count(*) FROM document_chunks dc
                    JOIN raw_documents rd ON dc.raw_document_id = rd.id
                    WHERE rd.company_id = %s
                """, (company_id,)).fetchone()[0]
                has_rag = rag_count > 0

                # Check prices
                if not has_price:
                    p_count = conn.execute("SELECT count(*) FROM prices p JOIN tickers t ON p.ticker_id = t.id WHERE t.symbol=%s", (ticker,)).fetchone()[0]
                    has_price = p_count > 0

            # Compute Data Quality Category
            quality = "Missing"
            
            # ETF/Core logic
            if asset_type == "ETF" or (notes and "core" in notes.lower()):
                if has_price:
                    quality = "Full (ETF)"
                else:
                    quality = "Partial (ETF Missing Price)"
            else:
                # Stock logic
                checks = [has_price, has_cik, has_facts, has_ratios, has_valuation, has_rag, has_memo]
                num_passed = sum(checks)
                
                if num_passed == len(checks):
                    quality = "Full"
                elif num_passed >= 2:
                    quality = "Partial"
                else:
                    quality = "Missing"

            coverage_data.append({
                "ticker": ticker,
                "asset_type": asset_type,
                "has_price": has_price,
                "has_cik": has_cik,
                "has_facts": has_facts,
                "has_ratios": has_ratios,
                "has_valuation": has_valuation,
                "has_rag": has_rag,
                "has_memo": has_memo,
                "data_quality": quality
            })
            
    # Generate Markdown Report
    md_lines = [f"# Portfolio Coverage Map: {portfolio_name}", ""]
    md_lines.append("| Ticker | Type | Price | CIK | Facts | Ratios | Val Scorecard | RAG | Memo | Data Quality |")
    md_lines.append("|---|---|---|---|---|---|---|---|---|---|")
    
    for c in coverage_data:
        md_lines.append(f"| **{c['ticker']}** | {c['asset_type']} | {'✅' if c['has_price'] else '❌'} | {'✅' if c['has_cik'] else '❌'} | {'✅' if c['has_facts'] else '❌'} | {'✅' if c['has_ratios'] else '❌'} | {'✅' if c['has_valuation'] else '❌'} | {'✅' if c['has_rag'] else '❌'} | {'✅' if c['has_memo'] else '❌'} | {c['data_quality']} |")
    
    md_path = reports_path / "portfolio_coverage.md"
    json_path = reports_path / "portfolio_coverage.json"
    
    md_path.write_text("\n".join(md_lines) + "\n")
    json_path.write_text(json.dumps(coverage_data, indent=2) + "\n")
    
    print("Coverage report generated:")
    print(f" - {md_path}")
    print(f" - {json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio", required=True, help="Name of the portfolio to analyze")
    parser.add_argument("--reports-dir", default=str(BACKEND.parent / "reports"))
    args = parser.parse_args()
    analyze_coverage(args.portfolio, args.reports_dir)
