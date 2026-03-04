from pydantic import BaseModel, EmailStr
from typing import Optional, Literal


class SignupIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    email: EmailStr
    plan: Literal["starter", "pro", "business"]


class GenerateIn(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    steps: int = 4
    guidance: float = 0.0


class JobOut(BaseModel):
    id: int
    status: str
    image_url: Optional[str] = None
    error: Optional[str] = None
