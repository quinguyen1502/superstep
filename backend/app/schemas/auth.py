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


class ResetRequest(BaseModel):  # TASK-0045
    email: str


class ResetConfirm(BaseModel):
    token: str
    password: str


class PasswordChange(BaseModel):  # TASK-0052
    current_password: str
    new_password: str


class TokenName(BaseModel):  # TASK-0167
    name: str


class DeviceStart(BaseModel):
    name: str | None = None


class DeviceDecision(BaseModel):
    user_code: str
    name: str | None = None
