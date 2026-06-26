from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class AnalysisCreateResponse(BaseModel):
    analysis_id: int
    status: str


class ProductResult(BaseModel):
    article: str
    name: str
    category: str
    purchase_price: Decimal
    sale_price: Decimal
    weight: Decimal
    sold: int
    returns: int
    net_revenue: Decimal
    commission: Decimal
    logistics_total: Decimal
    purchase_cost: Decimal
    profit: Decimal
    margin_pct: Decimal
    margin_zone: str

    model_config = {"from_attributes": True}


class AnalysisStatusResponse(BaseModel):
    analysis_id: int
    status: str
    created_at: datetime
    files_meta: dict[str, Any] | None = None
    results: list[ProductResult] | None = None


class AnalysisHistoryItem(BaseModel):
    analysis_id: int
    status: str
    created_at: datetime
    files_meta: dict[str, Any] | None = None
