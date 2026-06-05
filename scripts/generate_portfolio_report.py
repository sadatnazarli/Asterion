import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.portfolio.report_builder import build_portfolio_report, generate_markdown_report
from app.db.session import transaction

def main():
    parser = argparse.ArgumentParser(description="Generate Portfolio Risk & Policy Report")
    parser.add_argument("--portfolio", type=str, default="My Real Portfolio", help="Name of portfolio in DB")
    parser.add_argument("--reports-dir", type=str, default="reports", help="Directory for reports")
    args = parser.parse_args()

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(scripts_dir, '..'))
    
    if os.path.isabs(args.reports_dir):
        reports_dir = args.reports_dir
    else:
        reports_dir = os.path.join(project_root, args.reports_dir)
        
    os.makedirs(reports_dir, exist_ok=True)

    with transaction() as conn:
        res = conn.execute("""
            SELECT ticker, quantity, average_cost, current_price, current_value, value_source, asset_type, notes
            FROM portfolio_positions pp
            JOIN portfolios p ON pp.portfolio_id = p.id
            WHERE p.name = %s
        """, (args.portfolio,))
        rows = res.fetchall()

    if not rows:
        print(f"No positions found for portfolio: {args.portfolio}")
        sys.exit(1)

    positions = []
    for r in rows:
        positions.append({
            "ticker": r[0],
            "quantity": float(r[1]) if r[1] is not None else None,
            "average_cost": float(r[2]) if r[2] is not None else None,
            "current_price": float(r[3]) if r[3] is not None else None,
            "current_value": float(r[4]) if r[4] is not None else None,
            "value_source": r[5],
            "asset_type": r[6],
            "notes": r[7]
        })

    report_data = build_portfolio_report(positions, reports_dir=reports_dir)
    md_content = generate_markdown_report(report_data)

    basename = "my_real_portfolio_report"
    json_path = os.path.join(reports_dir, f"{basename}.json")
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2)

    md_path = os.path.join(reports_dir, f"{basename}.md")
    with open(md_path, "w") as f:
        f.write(md_content)

    print(f"Portfolio reports generated successfully:")
    print(f" - {json_path}")
    print(f" - {md_path}")

if __name__ == "__main__":
    main()
