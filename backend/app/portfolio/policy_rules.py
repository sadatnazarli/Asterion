from typing import List, Dict, Any
from .risk_metrics import (
    calculate_single_name_concentration,
    calculate_theme_concentration,
    calculate_speculative_exposure,
    calculate_core_etf_exposure
)

# Constants for thresholds
MAX_SINGLE_STOCK_PCT = 0.15
MAX_THEME_PCT = 0.25
MAX_SPECULATIVE_PCT = 0.10
MIN_CORE_ETF_PCT = 0.30

def check_portfolio_policies(positions: List[Dict[str, Any]]) -> List[str]:
    warnings = []
    
    # Check Single Stock
    single_name_weights = calculate_single_name_concentration(positions)
    for ticker, weight in single_name_weights.items():
        if weight > MAX_SINGLE_STOCK_PCT:
            warnings.append(
                f"Policy Warning: Single stock concentration for {ticker} ({weight:.2%}) "
                f"exceeds the {MAX_SINGLE_STOCK_PCT:.2%} maximum threshold."
            )
            
    # Check Theme
    theme_weights = calculate_theme_concentration(positions)
    for theme, weight in theme_weights.items():
        if weight > MAX_THEME_PCT:
            warnings.append(
                f"Policy Warning: Theme concentration for {theme} ({weight:.2%}) "
                f"exceeds the {MAX_THEME_PCT:.2%} maximum threshold."
            )
            
    # Check Speculative
    speculative_exposure = calculate_speculative_exposure(positions)
    if speculative_exposure > MAX_SPECULATIVE_PCT:
        warnings.append(
            f"Policy Warning: Speculative exposure ({speculative_exposure:.2%}) "
            f"exceeds the {MAX_SPECULATIVE_PCT:.2%} maximum threshold."
        )
        
    # Check Core ETF
    core_etf_exposure = calculate_core_etf_exposure(positions)
    if core_etf_exposure < MIN_CORE_ETF_PCT:
        warnings.append(
            f"Policy Warning: Core ETF exposure ({core_etf_exposure:.2%}) "
            f"is below the {MIN_CORE_ETF_PCT:.2%} minimum threshold."
        )
        
    return warnings
