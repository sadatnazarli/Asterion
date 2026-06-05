from dataclasses import dataclass
from typing import List

@dataclass
class AdvancedScoreSpec:
    key: str
    name: str
    priority: str  # P0, P1, P2, P3
    required_inputs: List[str]
    description: str = ""

class AdvancedScoreRegistry:
    def __init__(self):
        self.scores = {
            "operating_leverage_convexity": AdvancedScoreSpec("operating_leverage_convexity", "Operating Leverage Convexity", "P0", ["gross_margin", "revenue_growth_yoy"], "Measures operating leverage convexity"),
            "reflexivity_risk": AdvancedScoreSpec("reflexivity_risk", "Reflexivity Risk", "P0", ["current_ratio", "debt_to_equity"], "Measures reflexivity risk"),
            "misunderstood_change": AdvancedScoreSpec("misunderstood_change", "Misunderstood Change", "P0", ["sentiment_shift", "capex_growth"], "Measures misunderstood change"),
            "perception_shift": AdvancedScoreSpec("perception_shift", "Perception Shift", "P0", ["analyst_revisions", "earnings_surprise"], "Measures perception shift"),
            "narrative_entropy": AdvancedScoreSpec("narrative_entropy", "Narrative Entropy", "P0", ["management_tone_variance", "topic_dispersion"], "Measures narrative entropy"),
            "thesis_fragility": AdvancedScoreSpec("thesis_fragility", "Thesis Fragility", "P0", ["dcf_sensitivity_impact"], "Measures thesis fragility based on reverse DCF sensitivity impact"),
            "expectations_gap": AdvancedScoreSpec("expectations_gap", "Expectations Gap", "P1", ["implied_growth", "historical_growth_ttm"], "Reverse DCF expectations gap"),
            "crowding_risk": AdvancedScoreSpec("crowding_risk", "Crowding Risk", "P2", ["short_interest", "institutional_ownership"], "Measures crowding risk"),
            "supply_demand_imbalance": AdvancedScoreSpec("supply_demand_imbalance", "Supply Demand Imbalance", "P2", ["float_turnover", "insider_buying"], "Measures supply and demand imbalance"),
            "deep_learning_price_predictors": AdvancedScoreSpec("deep_learning_price_predictors", "Deep Learning Price Predictors", "P3", ["tick_data", "order_book_depth"], "DL based price predictions"),
        }

    def get_implementable_scores(self, available_data: List[str], max_priority: str = "P0") -> List[AdvancedScoreSpec]:
        """
        Returns a list of scores that can be implemented given the available data,
        enforcing priority levels.
        A score is implementable if its priority is <= max_priority AND
        at least one required input is available (to handle missing data gracefully).
        """
        priority_levels = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        max_level = priority_levels.get(max_priority, 0)
        
        implementable = []
        for spec in self.scores.values():
            spec_level = priority_levels.get(spec.priority, 99)
            if spec_level <= max_level:
                # We can implement it if at least one input is present or if it requires no inputs
                if not spec.required_inputs or any(req in available_data for req in spec.required_inputs):
                    implementable.append(spec)
        return implementable
