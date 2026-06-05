from pydantic import BaseModel, Field
from typing import List

class AnalystOutput(BaseModel):
    ticker: str = Field(description="The ticker symbol of the company being analyzed")
    agent_name: str = Field(description="The name or role of the agent producing this output")
    summary: str = Field(description="A concise summary of the analysis")
    key_points: List[str] = Field(description="List of the most important takeaways")
    evidence: List[str] = Field(description="Factual evidence extracted from the provided text to support the key points")
    citations: List[str] = Field(description="Exact citations of the source materials used")
    confidence: float = Field(description="Confidence level in the analysis, between 0.0 and 1.0")
    uncertainties: List[str] = Field(description="List of areas where data is missing or analysis is uncertain")
    red_flags: List[str] = Field(description="Any alarming details, inconsistencies, or risks discovered during analysis")
    what_would_change_my_mind: str = Field(description="A brief statement describing what new information would significantly alter this analysis")
