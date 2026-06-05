import os
import json
from typing import List, Dict, Any
from .risk_metrics import (
    calculate_portfolio_value,
    calculate_position_weights,
    calculate_sector_concentration,
    calculate_theme_concentration,
    calculate_speculative_exposure,
    calculate_core_etf_exposure,
    calculate_unrealized_pl_percentage,
    get_position_value
)
from .policy_rules import check_portfolio_policies

def load_m6_scorecard(ticker: str, reports_dir: str = "reports") -> Dict[str, Any]:
    path = os.path.join(reports_dir, f"{ticker.upper()}_valuation_scorecard.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def build_portfolio_report(positions: List[Dict[str, Any]], reports_dir: str = "reports") -> Dict[str, Any]:
    total_value = calculate_portfolio_value(positions)
    weights = calculate_position_weights(positions)
    sector_concentration = calculate_sector_concentration(positions)
    theme_concentration = calculate_theme_concentration(positions)
    speculative_exposure = calculate_speculative_exposure(positions)
    core_etf_exposure = calculate_core_etf_exposure(positions)
    unrealized_pl = calculate_unrealized_pl_percentage(positions)
    
    warnings = check_portfolio_policies(positions)
    
    scorecards = {}
    high_valuation_risk_count = 0
    total_fragility = 0.0
    fragility_count = 0
    
    for p in positions:
        ticker = p['ticker']
        sc = load_m6_scorecard(ticker, reports_dir)
        if sc:
            scorecards[ticker] = sc
            if sc.get("classification") == "valuation_risk_watchlist":
                high_valuation_risk_count += 1
                
            adv_scores = sc.get("advanced_scores", {})
            fragility_data = adv_scores.get("thesis_fragility", {})
            fragility = fragility_data.get("score")
            if fragility is not None:
                total_fragility += (fragility * weights.get(ticker, 0))
                fragility_count += 1
                
    portfolio_fragility = total_fragility if fragility_count > 0 else 0.0
    
    positions_summary = {}
    for p in positions:
        positions_summary[p['ticker']] = {
            "current_value": get_position_value(p),
            "value_source": p.get("value_source", "missing"),
            "quantity": p.get("quantity"),
            "average_cost": p.get("average_cost"),
            "current_price": p.get("current_price"),
            "asset_type": p.get("asset_type"),
            "notes": p.get("notes"),
        }

    report = {
        "summary": {
            "total_value": total_value,
            "speculative_exposure": speculative_exposure,
            "core_etf_exposure": core_etf_exposure,
            "portfolio_fragility_weighted": portfolio_fragility,
            "high_valuation_risk_positions": high_valuation_risk_count
        },
        "weights": weights,
        "positions": positions_summary,
        "sector_concentration": sector_concentration,
        "theme_concentration": theme_concentration,
        "unrealized_pl_percentage": unrealized_pl,
        "policy_warnings": warnings,
        "m6_scorecards_integrated": list(scorecards.keys())
    }
    return report

def generate_markdown_report(report_data: Dict[str, Any]) -> str:
    md = "# Portfolio Risk & Policy Report\n\n"
    
    md += "## Summary\n"
    summary = report_data["summary"]
    md += f"- **Total Value**: ${summary['total_value']:,.2f}\n"
    md += f"- **Speculative Exposure**: {summary['speculative_exposure']:.2%}\n"
    md += f"- **Core ETF Exposure**: {summary['core_etf_exposure']:.2%}\n"
    md += f"- **Weighted Portfolio Fragility (M6)**: {summary['portfolio_fragility_weighted']:.2f}\n"
    md += f"- **High Valuation Risk Positions**: {summary['high_valuation_risk_positions']}\n\n"
    
    md += "## Policy Warnings\n"
    if report_data["policy_warnings"]:
        for w in report_data["policy_warnings"]:
            md += f"- {w}\n"
    else:
        md += "- No policy violations detected.\n"
    md += "\n"
    
    md += "## Position Weights\n"
    for ticker, w in report_data["weights"].items():
        pl = report_data["unrealized_pl_percentage"].get(ticker, 0.0)
        md += f"- **{ticker}**: {w:.2%} (Unrealized P/L: {pl:.2%})\n"
    md += "\n"
    
    md += "## Concentration\n"
    md += "### Sectors\n"
    for s, w in report_data["sector_concentration"].items():
        md += f"- **{s}**: {w:.2%}\n"
    md += "### Themes\n"
    for t, w in report_data["theme_concentration"].items():
        md += f"- **{t}**: {w:.2%}\n"
    md += "\n"
    
    md += "## Integrated Scorecards\n"
    if report_data["m6_scorecards_integrated"]:
        md += f"Successfully integrated M6 scorecards for: {', '.join(report_data['m6_scorecards_integrated'])}\n"
    else:
        md += "No M6 scorecards found.\n"
        
    return md
