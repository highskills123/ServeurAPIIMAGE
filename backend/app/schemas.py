from pydantic import BaseModel, EmailStr, field_validator
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
    plan: Literal["free", "starter", "pro", "business"]


class GenerateIn(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    steps: int = 4
    guidance: float = 0.0

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Prompt must be at least 3 characters long (after trimming whitespace)")
        if len(v) > 500:
            raise ValueError("Prompt must not exceed 500 characters (after trimming whitespace)")
        return v

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        if v not in (256, 512, 768, 1024):
            raise ValueError("Dimension must be one of 256, 512, 768, 1024")
        return v

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: int) -> int:
        if not (1 <= v <= 50):
            raise ValueError("Steps must be between 1 and 50")
        return v


class JobOut(BaseModel):
    id: int
    status: str
    image_url: Optional[str] = None
    error: Optional[str] = None


class PlanInfo(BaseModel):
    name: str
    price_usd: float
    monthly_limit: int
    description: str


class CheckoutIn(BaseModel):
    plan: Literal["starter", "pro", "business"]
    success_url: str
    cancel_url: str
