import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..db import get_db
from ..deps import get_current_user
from ..models import User, ImageJob, JobStatus
from ..schemas import GenerateIn, JobOut
from ..billing import check_and_consume_image
from ..jobs.queue import q, redis_client
from ..jobs.tasks import run_generate
from ..storage import public_url_from_path
from ..config import settings

router = APIRouter(prefix="/images", tags=["images"])
limiter = Limiter(key_func=get_remote_address)

_CACHE_TTL = 86400  # 24 hours


def _prompt_cache_key(payload: GenerateIn) -> str:
    raw = f"{payload.prompt}|{payload.width}|{payload.height}|{payload.steps}|{payload.guidance}"
    return "prompt_cache:" + hashlib.sha256(raw.encode()).hexdigest()


@router.post("/generate", response_model=JobOut)
@limiter.limit(settings.GENERATE_RATE_LIMIT)
def generate(request: Request, payload: GenerateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ok, limit, used = check_and_consume_image(db, user, 1)
    if not ok:
        raise HTTPException(status_code=402, detail=f"Monthly limit reached ({used}/{limit}). Upgrade needed.")

    # Check prompt cache – reuse a previously generated image for the same prompt+params
    cache_key = _prompt_cache_key(payload)
    cached_path = redis_client.get(cache_key)
    if cached_path:
        image_path = cached_path.decode() if isinstance(cached_path, bytes) else cached_path
        job = ImageJob(
            user_id=user.id,
            prompt=payload.prompt,
            width=payload.width,
            height=payload.height,
            steps=payload.steps,
            guidance=payload.guidance,
            status=JobStatus.done,
            image_path=image_path,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        url = public_url_from_path(job.image_path)
        return JobOut(id=job.id, status=job.status.value, image_url=url)

    job = ImageJob(
        user_id=user.id,
        prompt=payload.prompt,
        width=payload.width,
        height=payload.height,
        steps=payload.steps,
        guidance=payload.guidance,
        status=JobStatus.queued,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    q.enqueue(run_generate, job.id, cache_key, _CACHE_TTL)

    return JobOut(id=job.id, status=job.status.value)


@router.get("/{job_id}", response_model=JobOut)
def status(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImageJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    url = public_url_from_path(job.image_path) if job.image_path else None
    return JobOut(id=job.id, status=job.status.value, image_url=url, error=job.error)


@router.get("/", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    jobs = db.query(ImageJob).filter(ImageJob.user_id == user.id).order_by(ImageJob.created_at.desc()).limit(100).all()
    out = []
    for j in jobs:
        out.append(JobOut(
            id=j.id,
            status=j.status.value,
            image_url=public_url_from_path(j.image_path) if j.image_path else None,
            error=j.error
        ))
    return out
