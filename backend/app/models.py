import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Plan(str, enum.Enum):
    free = "free"
    starter = "starter"
    pro = "pro"
    business = "business"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    plan: Mapped[Plan] = mapped_column(Enum(Plan), default=Plan.free)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    jobs: Mapped[list["ImageJob"]] = relationship(back_populates="user")


class UsageMonthly(Base):
    __tablename__ = "usage_monthly"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    yyyymm: Mapped[str] = mapped_column(String(6), index=True)  # "202603"
    images_used: Mapped[int] = mapped_column(Integer, default=0)


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class ImageJob(Base):
    __tablename__ = "image_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    prompt: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer, default=1024)
    height: Mapped[int] = mapped_column(Integer, default=1024)
    steps: Mapped[int] = mapped_column(Integer, default=4)
    guidance: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    user: Mapped[User] = relationship(back_populates="jobs")
