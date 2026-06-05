from pydantic import BaseModel, Field
from .citations import Citation
from typing import Optional

class EvidencePack(BaseModel):
    text: str = Field(..., description="The chunk text retrieved from the database")
    citation: Citation = Field(..., description="Citation metadata for the retrieved chunk")
    score: float = Field(0.0, description="The retrieval score (BM25 + Vector + Weights)")
    
    def to_formatted_string(self) -> str:
        """
        Formats the evidence into a string format suitable for passing to the LLM.
        """
        header = f"[Source: {self.citation.source_document} | Type: {self.citation.filing_type} | Date: {self.citation.filing_date}"
        if self.citation.section:
            header += f" | Section: {self.citation.section}"
        header += "]"
        
        return f"{header}\n{self.text}\n"
