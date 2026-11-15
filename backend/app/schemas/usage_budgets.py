from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from .envelope import Envelope

Scope = Literal["user", "team"]


class BudgetAmount(BaseModel):
    amount_usd: Decimal = Field(gt=0, max_digits=9, decimal_places=2)


class BudgetCreate(BudgetAmount):
    scope: Scope
    target_id: str = Field(min_length=1, max_length=128)


class BudgetTarget(BaseModel):
    scope: Scope
    id: str
    name: str


class BudgetView(BaseModel):
    id: str
    scope: Scope
    target_id: str
    name: str
    amount_usd: float
    spent_usd: float
    unpriced_rows: int


class BudgetList(BaseModel):
    month: str
    time_zone: str
    budgets: list[BudgetView]
    targets: list[BudgetTarget]


BudgetListEnvelope = Envelope[BudgetList]
