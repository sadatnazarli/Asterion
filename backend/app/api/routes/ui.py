from fastapi import APIRouter, HTTPException
import os
import json
from pathlib import Path

router = APIRouter()

REPORTS_DIR = Path(__file__).resolve().parents[4] / "reports"

@router.get("/reports")
def list_reports():
    if not REPORTS_DIR.exists():
        return {"reports": []}
        
    reports = []
    for file in sorted(REPORTS_DIR.glob("*")):
        if file.suffix in [".json", ".md"]:
            reports.append({
                "name": file.name,
                "type": file.suffix.lstrip("."),
                "size_bytes": file.stat().st_size
            })
    return {"reports": reports}

@router.get("/reports/{name}")
def get_report(name: str):
    file_path = REPORTS_DIR / name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
        
    if file_path.suffix == ".json":
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Invalid JSON file")
            
    elif file_path.suffix == ".md":
        try:
            with open(file_path, "r") as f:
                return {"content": f.read()}
        except Exception:
            raise HTTPException(status_code=500, detail="Could not read markdown file")
            
    raise HTTPException(status_code=400, detail="Unsupported file type")

from app.market.router import fetch_quote

@router.get("/portfolio/latest")
def get_latest_portfolio():
    file_path = REPORTS_DIR / "my_real_portfolio_report.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Portfolio report not found")
    with open(file_path, "r") as f:
        return json.load(f)

@router.get("/portfolio/live")
def get_live_portfolio():
    file_path = REPORTS_DIR / "my_real_portfolio_report.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Portfolio report not found")
    
    with open(file_path, "r") as f:
        report = json.load(f)
        
    positions = report.get("positions", {})
    live_holdings = []
    total_value = 0.0
    daily_pnl = 0.0
    total_pnl = 0.0
    has_cost_basis = False
    
    for ticker, pos in positions.items():
        quote = fetch_quote(ticker)
        current_price = quote.get("c") if quote else pos.get("current_price")
        prev_price = (current_price - quote.get("d", 0)) if quote and quote.get("d") is not None else current_price
        
        quantity = pos.get("quantity")
        avg_cost = pos.get("average_cost")
        val_source = pos.get("value_source", "missing")
        
        if val_source == "current_value_optional":
            # If we don't have shares, we can't accurately calculate PNL from price change directly
            # without knowing the starting value. We'll use the static value.
            pos_val = pos.get("current_value", 0)
            daily_change_pct = quote.get("dp", 0) if quote else 0
            pos_daily_pnl = pos_val * (daily_change_pct / 100.0)
        else:
            if quantity and current_price:
                pos_val = quantity * current_price
                pos_daily_pnl = quantity * (quote.get("d", 0) if quote else 0)
            else:
                pos_val = pos.get("current_value", 0)
                pos_daily_pnl = 0.0
                
        if quantity and avg_cost:
            has_cost_basis = True
            total_pnl += (pos_val - (quantity * avg_cost))
            
        total_value += pos_val
        daily_pnl += pos_daily_pnl
        
        live_holdings.append({
            "ticker": ticker,
            "name": ticker,
            "current_value": pos_val,
            "current_price": current_price,
            "daily_change_pct": quote.get("dp", 0) if quote else 0,
            "value_source": val_source,
            "theme": pos.get("notes"),
            "asset_type": pos.get("asset_type"),
            "risk_label": "Valuation Risk" if ticker in report.get("m6_scorecards_integrated", []) else None
        })
        
    for h in live_holdings:
        h["weight"] = h["current_value"] / total_value if total_value > 0 else 0

    return {
        "total_value": total_value,
        "daily_pnl": daily_pnl,
        "daily_pnl_pct": (daily_pnl / (total_value - daily_pnl) * 100) if (total_value - daily_pnl) > 0 else 0,
        "total_pnl": total_pnl if has_cost_basis else None,
        "cost_basis_missing": not has_cost_basis,
        "holdings": live_holdings
    }

def compute_contributors(live: dict) -> dict:
    """Pure: estimate each holding's dollar contribution to today's move.

    contribution = current_value * (daily_change_pct / 100). Works with
    current_value_optional positions (no shares needed). Returns ranked positive
    and negative contributors plus the unexplained gap vs the reported daily P/L.
    """
    holdings = live.get("holdings", []) or []
    rows = []
    for h in holdings:
        val = h.get("current_value") or 0.0
        dp = h.get("daily_change_pct") or 0.0
        contrib = val * (dp / 100.0)
        rows.append(
            {
                "ticker": h.get("ticker"),
                "current_value": val,
                "daily_change_pct": dp,
                "estimated_contribution_dollars": contrib,
                "direction": "up" if contrib > 0 else "down" if contrib < 0 else "flat",
                "theme": h.get("theme"),
            }
        )
    rows.sort(key=lambda r: r["estimated_contribution_dollars"], reverse=True)
    positive = [r for r in rows if r["estimated_contribution_dollars"] > 0]
    negative = [r for r in rows if r["estimated_contribution_dollars"] < 0]
    sum_contrib = sum(r["estimated_contribution_dollars"] for r in rows)
    reported = live.get("daily_pnl", 0.0) or 0.0
    return {
        "total_value": live.get("total_value", 0.0),
        "daily_pnl_reported": reported,
        "sum_contributions": sum_contrib,
        "unexplained_difference": reported - sum_contrib,
        "top_positive": positive[:3],
        "top_negative": list(reversed(negative))[:3],
        "all": rows,
    }


@router.get("/portfolio/contributors")
def get_portfolio_contributors():
    """Why did the portfolio move today — ranked per-holding dollar contribution."""
    live = get_live_portfolio()
    return compute_contributors(live)


@router.get("/portfolio/coverage")
def get_portfolio_coverage():
    file_path = REPORTS_DIR / "portfolio_coverage.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Coverage report not found")
    with open(file_path, "r") as f:
        return {"coverage": json.load(f)}

@router.get("/tickers/{ticker}/scorecard")
def get_ticker_scorecard(ticker: str):
    file_path = REPORTS_DIR / f"{ticker.upper()}_scorecard.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Scorecard not found")
    with open(file_path, "r") as f:
        return json.load(f)

@router.get("/tickers/{ticker}/valuation")
def get_ticker_valuation(ticker: str):
    file_path = REPORTS_DIR / f"{ticker.upper()}_valuation_scorecard.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Valuation scorecard not found")
    with open(file_path, "r") as f:
        return json.load(f)
