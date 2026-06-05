# NVDA Valuation Scorecard (M10 — real inputs)

**Date:** 2026-06-04 14:24 UTC

**Classification:** wait_for_better_price  ·  confidence 0.75

**Reason:** Business is solid but current valuation multiples and expectations gap suggest limited margin of safety.

**Market cap:** 5196950000000.0  ·  price used 214.75

**Input missing flags:** none

## Advanced scores (real)

### operating_leverage_convexity
- score: 100.0
- confidence: 1.00
- missing: none
- Operating leverage from GM×growth + op-leverage 0.92× (deleveraging), op-margin rising. Score: 100.0

### reflexivity_risk
- score: 14.0
- confidence: 1.00
- missing: none
- Financial reflexivity from leverage/liquidity + dilution +872.0% (MVP — not true reflexivity). Risk: 14.0

### expectations_gap
- score: 0.0
- confidence: 1.00
- missing: none
- Implied growth +24.5% vs historical +81.0% + PE 43. Score: 0.0

### thesis_fragility
- score: 41.1
- confidence: 1.00
- missing: none
- Fragility blend of sensitivity 0.55, valuation 0.72, dilution 1.00. Score: 41.1

### misunderstood_change
- score: 100.0
- confidence: 0.50
- missing: sentiment_shift
- Misunderstood change: capex +137.7% (sentiment feed missing — weak). Score: 100.0

## Real metrics used

- capex: 6042000000.0
- capex_concept: PaymentsToAcquireProductiveAssets
- capex_growth: 1.3773958916100493
- current_ratio: 3.905263812455306
- dcf_sensitivity_impact: 0.5511313453555936
- debt_to_equity: 0.05383583503398117
- enterprise_value: 5194813000000.0
- fcf: 96676000000.0
- fcf_confidence: 1.0
- fcf_growth: 0.8915099395977031
- fcf_margin: 0.44770258129648327
- fcf_margin_trend: 0.004168225891210964
- gross_margin: 0.7106808435754708
- gross_margin_trend: -0.016494889328898754
- historical_growth_ttm: 0.8096431416698507
- implied_growth: 0.24508810897969038
- max_drawdown: -0.20214387999661532
- net_margin: 0.5560253406070261
- ocf_concept: NetCashProvidedByUsedInOperatingActivities
- operating_cash_flow: 102718000000.0
- operating_income_growth_yoy: 0.6007636305599549
- operating_leverage_ratio: 0.9175671106047734
- operating_margin: 0.6038168363141272
- operating_margin_trend: 0.06260019864628963
- pe_ratio: 43.28374990630231
- revenue_cagr: 0.8826841275109014
- revenue_growth_yoy: 0.6547353579009478
- sbc_to_revenue: 0.029573303448211987
- shares_change: 8.72
- volatility: 0.34604536903832883
- wacc: 0.11485515610150641
- wacc_assumptions: {'wacc': 0.11485515610150641, 'method': 'capm_phase_a', 'risk_free_rate': 0.045, 'equity_risk_premium': 0.05, 'beta': 1.4, 'beta_source': 'sector_fallback:semiconductor', 'cost_of_equity': 0.11499999999999999, 'cost_of_debt': 0.030585734529995277, 'cost_of_debt_source': 'interest_expense/total_debt', 'tax_rate': 0.1511700247437257, 'tax_rate_source': 'income_tax/pretax', 'weight_equity': 0.9983732334271714, 'weight_debt': 0.0016267665728285413, 'confidence': 1.0, 'missing_flags': []}
- wacc_confidence: 1.0

> Generated from SEC facts + reverse-DCF + price history. No mock constants.
