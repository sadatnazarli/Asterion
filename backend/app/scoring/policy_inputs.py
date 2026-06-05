from typing import Dict, Any
from backend.app.scoring.advanced_registry import AdvancedScoreRegistry
from backend.app.scoring.advanced_inputs import AdvancedInputsFetcher
from backend.app.scoring import advanced_scores
from backend.app.scoring.expectations_gap import calculate_expectations_gap
from backend.app.scoring.thesis_fragility import calculate_thesis_fragility

class PolicyCoordinator:
    def __init__(self):
        self.registry = AdvancedScoreRegistry()
        self.fetcher = AdvancedInputsFetcher()
        self.score_functions = {
            "operating_leverage_convexity": advanced_scores.calculate_operating_leverage_convexity,
            "reflexivity_risk": advanced_scores.calculate_reflexivity_risk,
            "misunderstood_change": advanced_scores.calculate_misunderstood_change,
            "perception_shift": advanced_scores.calculate_perception_shift,
            "narrative_entropy": advanced_scores.calculate_narrative_entropy,
            "thesis_fragility": calculate_thesis_fragility,
            "expectations_gap": calculate_expectations_gap
        }

    def evaluate_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Fetches all available inputs, determines which scores can be computed,
        computes them, and returns the final scorecard.
        """
        inputs = self.fetcher.fetch_all_inputs(ticker)
        available_keys = list(inputs.keys())
        
        implementable = self.registry.get_implementable_scores(available_keys)
        
        results = {}
        for spec in implementable:
            if spec.key in self.score_functions:
                func = self.score_functions[spec.key]
                results[spec.key] = func(inputs)
            else:
                # Mock output for scores without functions implemented yet (e.g. P1, P2)
                results[spec.key] = {
                    "score": 50.0,
                    "confidence": 0.0,
                    "inputs_used": {},
                    "missing_inputs": spec.required_inputs,
                    "explanation": "Function not implemented.",
                    "failure_modes": ["Not implemented"]
                }
                
        return {
            "ticker": ticker,
            "raw_inputs": inputs,
            "scores": results
        }
