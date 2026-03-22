import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..db import get_db
from ..deps import get_current_user
from ..models import User, ImageJob, JobStatus, JobType
from ..schemas import GenerateIn, SpritesheetIn, GameAssetIn, JobOut
from ..billing import check_and_consume_image
from ..jobs.queue import q, redis_client
from ..jobs.tasks import run_generate, run_generate_spritesheet, run_generate_game_asset
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
        return JobOut(id=job.id, status=job.status.value, job_type=job.job_type.value, image_url=url)

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

    q.enqueue(run_generate, job.id, cache_key, _CACHE_TTL, payload.negative_prompt)

    return JobOut(id=job.id, status=job.status.value, job_type=job.job_type.value)


@router.post("/spritesheet", response_model=JobOut)
@limiter.limit(settings.GENERATE_RATE_LIMIT)
def generate_spritesheet_endpoint(
    request: Request,
    payload: SpritesheetIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a sprite sheet containing rows×cols frames of the requested subject.

    Each frame counts as one image against the user's monthly quota, so a 2×4
    sheet consumes 8 images.  The output is a single PNG file with all frames
    arranged in a grid.
    """
    frame_count = payload.rows * payload.cols
    ok, limit, used = check_and_consume_image(db, user, frame_count)
    if not ok:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly limit reached ({used}/{limit}). "
                   f"This sprite sheet requires {frame_count} images. Upgrade needed.",
        )

    sheet_width = payload.cols * payload.frame_width
    sheet_height = payload.rows * payload.frame_height

    job = ImageJob(
        user_id=user.id,
        prompt=payload.prompt,
        width=sheet_width,
        height=sheet_height,
        steps=payload.steps,
        guidance=payload.guidance,
        job_type=JobType.spritesheet,
        rows=payload.rows,
        cols=payload.cols,
        status=JobStatus.queued,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    q.enqueue(run_generate_spritesheet, job.id, payload.negative_prompt, payload.style)

    return JobOut(id=job.id, status=job.status.value, job_type=job.job_type.value)


@router.post("/game-asset", response_model=JobOut)
@limiter.limit(settings.GENERATE_RATE_LIMIT)
def generate_game_asset_endpoint(
    request: Request,
    payload: GameAssetIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a mobile game asset (character, item, background, icon, or UI element).

    The asset type and size preset determine the output dimensions and the prompt
    prefix injected before the user's description so the model produces output
    suitable for direct use in a mobile game.
    """
    ok, limit, used = check_and_consume_image(db, user, 1)
    if not ok:
        raise HTTPException(status_code=402, detail=f"Monthly limit reached ({used}/{limit}). Upgrade needed.")

    # Resolve dimensions from asset type + size so the worker can call generate_image
    from ..ai.pipeline import _ASSET_DIMENSIONS
    dims = _ASSET_DIMENSIONS.get(payload.asset_type, {}).get(payload.size, (512, 512))
    width, height = dims

    job = ImageJob(
        user_id=user.id,
        prompt=payload.prompt,
        width=width,
        height=height,
        steps=payload.steps,
        guidance=payload.guidance,
        job_type=JobType.game_asset,
        status=JobStatus.queued,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    q.enqueue(run_generate_game_asset, job.id, payload.asset_type, payload.size, payload.style, payload.negative_prompt)

    return JobOut(id=job.id, status=job.status.value, job_type=job.job_type.value)


@router.get("/{job_id}", response_model=JobOut)
def status(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(ImageJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    url = public_url_from_path(job.image_path) if job.image_path else None
    return JobOut(id=job.id, status=job.status.value, job_type=job.job_type.value, image_url=url, error=job.error)


@router.get("/", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    jobs = db.query(ImageJob).filter(ImageJob.user_id == user.id).order_by(ImageJob.created_at.desc()).limit(100).all()
    out = []
    for j in jobs:
        out.append(JobOut(
            id=j.id,
            status=j.status.value,
            job_type=j.job_type.value,
            image_url=public_url_from_path(j.image_path) if j.image_path else None,
            error=j.error
        ))
    return out
