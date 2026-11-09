from pydantic import BaseModel


class Credentials(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str


class TokenOut(BaseModel):
    token: str
    user: UserOut


class ResetRequest(BaseModel):
    email: str


class ResetConfirm(BaseModel):
    token: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class TokenName(BaseModel):
    name: str


class DeviceStart(BaseModel):
    name: str | None = None


class DeviceDecision(BaseModel):
    user_code: str
    name: str | None = None
