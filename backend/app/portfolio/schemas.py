from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class PortfolioBase(BaseModel):
    name: str

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioResponse(PortfolioBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PortfolioPositionBase(BaseModel):
    ticker: str
    quantity: Optional[float] = None
    average_cost: Optional[float] = None
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    value_source: Optional[str] = None
    asset_type: Optional[str] = None
    notes: Optional[str] = None

class PortfolioPositionCreate(PortfolioPositionBase):
    portfolio_id: int

class PortfolioPositionResponse(PortfolioPositionBase):
    id: int
    portfolio_id: int
    model_config = ConfigDict(from_attributes=True)


class PortfolioSnapshotBase(BaseModel):
    asof_date: date
    total_value: float
    cash_balance: float = 0.0

class PortfolioSnapshotCreate(PortfolioSnapshotBase):
    portfolio_id: int

class PortfolioSnapshotResponse(PortfolioSnapshotBase):
    id: int
    portfolio_id: int
    model_config = ConfigDict(from_attributes=True)


class PortfolioRiskMetricBase(BaseModel):
    metric_name: str
    value: float

class PortfolioRiskMetricCreate(PortfolioRiskMetricBase):
    portfolio_id: int

class PortfolioRiskMetricResponse(PortfolioRiskMetricBase):
    id: int
    portfolio_id: int
    computed_at: datetime
    model_config = ConfigDict(from_attributes=True)
