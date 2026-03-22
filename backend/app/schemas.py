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
    negative_prompt: str = ""

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

    @field_validator("negative_prompt")
    @classmethod
    def validate_negative_prompt(cls, v: str) -> str:
        if len(v) > 300:
            raise ValueError("negative_prompt must not exceed 300 characters")
        return v


class SpritesheetIn(BaseModel):
    prompt: str
    rows: int = 2
    cols: int = 4
    frame_width: int = 128
    frame_height: int = 128
    steps: int = 4
    guidance: float = 0.0
    negative_prompt: str = ""

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Prompt must be at least 3 characters long (after trimming whitespace)")
        if len(v) > 500:
            raise ValueError("Prompt must not exceed 500 characters (after trimming whitespace)")
        return v

    @field_validator("rows", "cols")
    @classmethod
    def validate_grid(cls, v: int) -> int:
        if not (1 <= v <= 8):
            raise ValueError("rows and cols must be between 1 and 8")
        return v

    @field_validator("frame_width", "frame_height")
    @classmethod
    def validate_frame_dimensions(cls, v: int) -> int:
        if v not in (64, 128, 256):
            raise ValueError("frame_width and frame_height must be one of 64, 128, 256")
        return v

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: int) -> int:
        if not (1 <= v <= 50):
            raise ValueError("Steps must be between 1 and 50")
        return v

    @field_validator("negative_prompt")
    @classmethod
    def validate_negative_prompt(cls, v: str) -> str:
        if len(v) > 300:
            raise ValueError("negative_prompt must not exceed 300 characters")
        return v


class GameAssetIn(BaseModel):
    prompt: str
    asset_type: Literal[
        # Generic mobile-game types (original)
        "character", "item", "background", "icon", "ui_element",
        # RPG-specific types
        "hero", "enemy", "npc", "map_tile", "weapon", "armor", "boss", "portrait",
    ] = "character"
    size: Literal["small", "medium", "large"] = "medium"
    style: str = "2D mobile game art"
    steps: int = 4
    guidance: float = 0.0
    negative_prompt: str = ""

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Prompt must be at least 3 characters long (after trimming whitespace)")
        if len(v) > 500:
            raise ValueError("Prompt must not exceed 500 characters (after trimming whitespace)")
        return v

    @field_validator("style")
    @classmethod
    def validate_style(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            raise ValueError("style must not exceed 100 characters")
        return v

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: int) -> int:
        if not (1 <= v <= 50):
            raise ValueError("Steps must be between 1 and 50")
        return v

    @field_validator("negative_prompt")
    @classmethod
    def validate_negative_prompt(cls, v: str) -> str:
        if len(v) > 300:
            raise ValueError("negative_prompt must not exceed 300 characters")
        return v


class JobOut(BaseModel):
    id: int
    status: str
    job_type: str = "image"
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
