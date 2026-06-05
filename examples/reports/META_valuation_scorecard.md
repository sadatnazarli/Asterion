# META Valuation Scorecard (M10 — real inputs)

**Date:** 2026-06-04 14:24 UTC

**Classification:** wait_for_better_price  ·  confidence 0.75

**Reason:** Business is solid but current valuation multiples and expectations gap suggest limited margin of safety.

**Market cap:** 1578631270507.8125  ·  price used 622.97998046875

**Input missing flags:** gross_margin

## Advanced scores (real)

### operating_leverage_convexity
- score: 47.1
- confidence: 0.50
- missing: gross_margin
- Operating leverage from GM×growth + op-leverage 0.90× (deleveraging), op-margin falling. Score: 47.1

### reflexivity_risk
- score: 18.9
- confidence: 1.00
- missing: none
- Financial reflexivity from leverage/liquidity + SBC 10.2% of revenue, drawdown -33% (MVP — not true reflexivity). Risk: 18.9

### expectations_gap
- score: 65.6
- confidence: 1.00
- missing: none
- Implied growth +14.0% vs historical +9.9% + PE 26, FCF margin slipping. Score: 65.6

### thesis_fragility
- score: 47.6
- confidence: 1.00
- missing: none
- Fragility blend of sensitivity 0.61, margin 0.60, dilution 0.68. Score: 47.6

### misunderstood_change
- score: 100.0
- confidence: 0.50
- missing: sentiment_shift
- Misunderstood change: capex +87.1% (sentiment feed missing — weak). Score: 100.0

## Real metrics used

- capex: 69691000000.0
- capex_concept: PaymentsToAcquirePropertyPlantAndEquipment
- capex_growth: 0.8705980244792786
- current_ratio: 2.5987666124868536
- dcf_sensitivity_impact: 0.6132599544972456
- debt_to_equity: 0.27040687156778354
- enterprise_value: 1601502270507.8125
- fcf: 46109000000.0
- fcf_confidence: 1.0
- fcf_growth: -0.1472666074863146
- fcf_margin: 0.2294368201586338
- fcf_margin_trend: -0.0992663488190624
- historical_growth_ttm: 0.09869138749286992
- implied_growth: 0.13982891397834143
- max_drawdown: -0.33296879207231944
- net_margin: 0.3008369574952977
- ocf_concept: NetCashProvidedByUsedInOperatingActivities
- operating_cash_flow: 115800000000.0
- operating_income_growth_yoy: 0.20028826751225126
- operating_leverage_ratio: 0.903540937722003
- operating_margin: 0.41437855159579234
- operating_margin_trend: -0.0073818024446086206
- pe_ratio: 26.111205638754384
- revenue_cagr: 0.22167038498246217
- revenue_growth_yoy: 0.22167038498246217
- sbc_to_revenue: 0.10164405919409253
- volatility: 0.3565016058583477
- wacc: 0.09447035632454541
- wacc_assumptions: {'wacc': 0.09447035632454541, 'method': 'capm_phase_a', 'risk_free_rate': 0.045, 'equity_risk_premium': 0.05, 'beta': 1.05, 'beta_source': 'sector_fallback:mega_cap_tech', 'cost_of_equity': 0.0975, 'cost_of_debt': 0.018555086476916793, 'cost_of_debt_source': 'interest_expense/total_debt', 'tax_rate': 0.2964436996695061, 'tax_rate_source': 'income_tax/pretax', 'weight_equity': 0.9641230687563876, 'weight_debt': 0.035876931243612374, 'confidence': 1.0, 'missing_flags': []}
- wacc_confidence: 1.0

> Generated from SEC facts + reverse-DCF + price history. No mock constants.
