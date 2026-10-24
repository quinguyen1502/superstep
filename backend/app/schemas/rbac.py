from typing import Optional
from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    role: Optional[str] = Field(None, max_length=20)
    active: Optional[bool] = None


class ShareIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    role: str = Field("viewer", max_length=20)


class TeamShareIn(BaseModel):
    team_id: str = Field(..., min_length=1, max_length=40)
    role: str = Field("viewer", max_length=20)


class TeamIn(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=400)


class MemberIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)


class TransferIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    rebind: dict[str, str] = Field(default_factory=dict)
    keep_access: bool = True


class UserDelete(BaseModel):
    mode: str = Field("anonymize", max_length=20)
    reassign_to: Optional[str] = Field(None, max_length=254)


class PolicyIn(BaseModel):
    org_resources_roles: list[str]


class LangSmithIn(BaseModel):
    evals: bool
