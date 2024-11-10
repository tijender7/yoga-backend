from pydantic import BaseModel, EmailStr

class EmailCheck(BaseModel):
    email: EmailStr

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    username: str
    name: str
    phone: str | None = None
    healthConditions: str | None = None
    interest: str | None = None
    source: str | None = None