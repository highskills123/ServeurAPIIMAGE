from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models import UsageMonthly, User, Plan
from .config import settings


def yyyymm_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m")


def plan_limit(plan: Plan) -> int:
    if plan == Plan.free:
        return settings.FREE_MONTHLY_LIMIT
    if plan == Plan.starter:
        return settings.STARTER_MONTHLY_LIMIT
    if plan == Plan.pro:
        return settings.PRO_MONTHLY_LIMIT
    return settings.BUSINESS_MONTHLY_LIMIT


def check_and_consume_image(db: Session, user: User, count: int = 1):
    key = yyyymm_now()
    row = db.query(UsageMonthly).filter(
        UsageMonthly.user_id == user.id, UsageMonthly.yyyymm == key
    ).first()
    if not row:
        row = UsageMonthly(user_id=user.id, yyyymm=key, images_used=0)
        db.add(row)
        db.commit()
        db.refresh(row)

    limit = plan_limit(user.plan)
    if row.images_used + count > limit:
        return False, limit, row.images_used

    row.images_used += count
    db.commit()
    return True, limit, row.images_used
