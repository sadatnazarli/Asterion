from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class Citation(BaseModel):
    source_document: str = Field(..., description="Name of the source document, e.g., PLTR-2023-10K.html")
    filing_type: str = Field(..., description="Type of the filing, e.g., 10-K, 10-Q")
    filing_date: date = Field(..., description="Date of the filing")
    section: Optional[str] = Field(None, description="Section of the document, e.g., Risk Factors")
    accession_number: str = Field(..., description="Accession number of the SEC filing")
    chunk_id: Optional[str] = Field(None, description="UUID of the specific chunk in the database")
