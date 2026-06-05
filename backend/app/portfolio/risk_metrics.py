from typing import List, Dict, Any

def get_position_value(p: Dict[str, Any]) -> float:
    # Use explicitly stored current_value if available, else calculate
    if p.get('current_value') is not None:
        return float(p['current_value'])
    q = p.get('quantity')
    c = p.get('current_price')
    if q is not None and c is not None:
        return float(q * c)
    return 0.0

def calculate_portfolio_value(positions: List[Dict[str, Any]]) -> float:
    return sum(get_position_value(p) for p in positions)

def calculate_position_weights(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    total_value = calculate_portfolio_value(positions)
    if total_value == 0:
        return {}
    
    weights = {}
    for p in positions:
        pos_value = get_position_value(p)
        weights[p['ticker']] = pos_value / total_value
    return weights

def calculate_concentration_by_key(positions: List[Dict[str, Any]], key: str) -> Dict[str, float]:
    total_value = calculate_portfolio_value(positions)
    if total_value == 0:
        return {}
    
    concentration = {}
    for p in positions:
        val = p.get(key)
        if not val:
            continue
        pos_value = get_position_value(p)
        concentration[val] = concentration.get(val, 0.0) + (pos_value / total_value)
    return concentration

def calculate_sector_concentration(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    return calculate_concentration_by_key(positions, 'asset_type')

def calculate_theme_concentration(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    return calculate_concentration_by_key(positions, 'notes')

def calculate_single_name_concentration(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    return calculate_position_weights(positions)

def calculate_speculative_exposure(positions: List[Dict[str, Any]]) -> float:
    total_value = calculate_portfolio_value(positions)
    if total_value == 0:
        return 0.0
    
    # Check notes for speculative themes
    spec_value = sum(get_position_value(p) for p in positions if p.get('notes') and ('speculative' in p['notes'].lower() or 'biotech' in p['notes'].lower()))
    return spec_value / total_value

def calculate_core_etf_exposure(positions: List[Dict[str, Any]]) -> float:
    total_value = calculate_portfolio_value(positions)
    if total_value == 0:
        return 0.0
    
    core_value = sum(get_position_value(p) for p in positions if p.get('notes') and 'core' in p['notes'].lower())
    return core_value / total_value

def calculate_unrealized_pl_percentage(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    pl_pct = {}
    total_cost = 0.0
    total_current = 0.0
    
    ticker_cost = {}
    ticker_current = {}
    
    for p in positions:
        q = p.get('quantity')
        c = p.get('average_cost')
        if q is None or c is None:
            continue # Missing cost basis
        
        cost = float(q * c)
        current = get_position_value(p)
        
        t = p['ticker']
        ticker_cost[t] = ticker_cost.get(t, 0.0) + cost
        ticker_current[t] = ticker_current.get(t, 0.0) + current
        
        total_cost += cost
        total_current += current
        
    for t in ticker_cost:
        if ticker_cost[t] > 0:
            pl_pct[t] = (ticker_current[t] - ticker_cost[t]) / ticker_cost[t]
        else:
            pl_pct[t] = 0.0
            
    if total_cost > 0:
        pl_pct['TOTAL'] = (total_current - total_cost) / total_cost
    else:
        pl_pct['TOTAL'] = 0.0
        
    return pl_pct
