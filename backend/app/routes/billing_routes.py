from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import User, Plan
from ..schemas import PlanInfo, CheckoutIn

router = APIRouter(prefix="/billing", tags=["billing"])

_PLANS: list[PlanInfo] = [
    PlanInfo(name="free",     price_usd=0.0,  monthly_limit=20,   description="20 images/month – free forever"),
    PlanInfo(name="starter",  price_usd=9.0,  monthly_limit=300,  description="300 images/month"),
    PlanInfo(name="pro",      price_usd=29.0, monthly_limit=1000, description="1 000 images/month"),
    PlanInfo(name="business", price_usd=99.0, monthly_limit=5000, description="5 000 images/month"),
]


def _stripe_price_id(plan: str) -> str | None:
    return {
        "starter":  settings.STRIPE_PRICE_STARTER_ID,
        "pro":      settings.STRIPE_PRICE_PRO_ID,
        "business": settings.STRIPE_PRICE_BUSINESS_ID,
    }.get(plan)


@router.get("/plans", response_model=list[PlanInfo])
def list_plans():
    """Return all available plans with pricing."""
    return _PLANS


@router.post("/checkout")
def create_checkout(
    payload: CheckoutIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout Session to upgrade the authenticated user."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Payments not configured")

    price_id = _stripe_price_id(payload.plan)
    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"No Stripe price configured for plan '{payload.plan}'. "
                   "Set STRIPE_PRICE_{PLAN}_ID in your environment.",
        )

    import stripe  # lazy import – only needed when Stripe is configured
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Retrieve or create the Stripe customer for this user
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(email=user.email)
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
        metadata={"user_id": str(user.id), "plan": payload.plan},
    )
    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events (subscription created/updated/deleted)."""
    payload = await request.body()

    if settings.STRIPE_WEBHOOK_SECRET:
        import stripe
        sig = request.headers.get("stripe-signature", "")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        import json
        event = json.loads(payload)

    event_type = event.get("type", "")

    if event_type in ("checkout.session.completed", "customer.subscription.updated"):
        data = event["data"]["object"]
        user_id = int(data.get("metadata", {}).get("user_id", 0))
        plan_name = data.get("metadata", {}).get("plan", "")
        if user_id and plan_name and plan_name in Plan.__members__:
            user = db.get(User, user_id)
            if user:
                user.plan = Plan(plan_name)
                # Persist Stripe customer ID if not yet stored
                customer_id = data.get("customer")
                if customer_id and not user.stripe_customer_id:
                    user.stripe_customer_id = customer_id
                db.commit()

    elif event_type == "customer.subscription.deleted":
        data = event["data"]["object"]
        customer_id = data.get("customer")
        if customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if user:
                user.plan = Plan.free
                db.commit()

    return {"received": True}
