"""Reverse DCF Model.

Solves for the implied growth rate required to justify a company's current Enterprise Value.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import root_scalar


def implied_growth_rate(
    enterprise_value: float,
    fcf: float,
    discount_rate: float = 0.10,
    terminal_growth: float = 0.025,
    horizon: int = 10,
) -> float | None:
    """Solve for the implied FCF growth rate using a Reverse DCF model.

    Args:
        enterprise_value: Current Enterprise Value.
        fcf: Current or normalized Free Cash Flow.
        discount_rate: WACC or required rate of return.
        terminal_growth: Long-term growth rate after the horizon.
        horizon: Number of years for the explicit forecast period.

    Returns:
        The implied annual growth rate (as a decimal), or None if it cannot be solved.
    """
    if fcf <= 0 or enterprise_value <= 0:
        return None

    if discount_rate <= terminal_growth:
        # Invalid setup for Gordon Growth Model
        return None

    def ev_error(g: float) -> float:
        # Calculate PV of FCFs
        years = np.arange(1, horizon + 1)
        fcf_forecast = fcf * (1 + g) ** years
        discount_factors = (1 + discount_rate) ** years
        pv_fcf = np.sum(fcf_forecast / discount_factors)

        # Calculate PV of Terminal Value
        fcf_terminal = fcf_forecast[-1] * (1 + terminal_growth)
        tv = fcf_terminal / (discount_rate - terminal_growth)
        pv_tv = tv / ((1 + discount_rate) ** horizon)

        implied_ev = pv_fcf + pv_tv
        return float(implied_ev - enterprise_value)

    # Use a root finding algorithm (bisection) to find g. 
    # Plausible range for growth: -100% to +1000%
    try:
        res = root_scalar(ev_error, bracket=[-0.99, 10.0], method='brentq')
        if res.converged:
            return float(res.root)
    except ValueError:
        pass

    return None


def reverse_dcf_sensitivity(
    enterprise_value: float,
    fcf: float,
    discount_rates: list[float] | None = None,
    terminal_growths: list[float] | None = None,
    horizon: int = 10,
) -> dict[str, list]:
    """Generate a sensitivity table for implied growth rates.

    Args:
        enterprise_value: Current Enterprise Value.
        fcf: Current or normalized Free Cash Flow.
        discount_rates: List of discount rates to test.
        terminal_growths: List of terminal growth rates to test.
        horizon: Explicit forecast period in years.

    Returns:
        A dictionary with 'discount_rates', 'terminal_growths', and a 2D matrix 'implied_growth_matrix'.
    """
    if discount_rates is None:
        discount_rates = [0.08, 0.09, 0.10, 0.11, 0.12]
    if terminal_growths is None:
        terminal_growths = [0.015, 0.02, 0.025, 0.03, 0.035]

    matrix = []
    for dr in discount_rates:
        row = []
        for tg in terminal_growths:
            g = implied_growth_rate(
                enterprise_value=enterprise_value,
                fcf=fcf,
                discount_rate=dr,
                terminal_growth=tg,
                horizon=horizon
            )
            row.append(g)
        matrix.append(row)

    return {
        "discount_rates": discount_rates,
        "terminal_growths": terminal_growths,
        "implied_growth_matrix": matrix
    }
