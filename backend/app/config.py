from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str

    JWT_SECRET: str
    JWT_EXPIRES_MIN: int = 60 * 24 * 7

    DATA_DIR: str = "/data"
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_STARTER_ID: str | None = None
    STRIPE_PRICE_PRO_ID: str | None = None
    STRIPE_PRICE_BUSINESS_ID: str | None = None

    FREE_MONTHLY_LIMIT: int = 20
    STARTER_MONTHLY_LIMIT: int = 300
    PRO_MONTHLY_LIMIT: int = 1000
    BUSINESS_MONTHLY_LIMIT: int = 5000

    GENERATE_RATE_LIMIT: str = "20/minute"

    MODEL_ID: str = "stabilityai/sdxl-turbo"
    DEFAULT_STEPS: int = 4
    DEFAULT_GUIDANCE: float = 0.0
    DEFAULT_WIDTH: int = 1024
    DEFAULT_HEIGHT: int = 1024

    class Config:
        env_file = ".env"


settings = Settings()
