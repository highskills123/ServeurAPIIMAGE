from fastapi import APIRouter, Request
from ..config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    # Skeleton : tu pourras ensuite
    # 1) vérifier la signature webhook
    # 2) passer le user en pro/business selon subscription
    # 3) reset quotas mensuels si tu veux
    payload = await request.body()
    return {"received": True, "bytes": len(payload)}
