from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..deps import get_current_user
from ..models import User, ImageJob, JobStatus
from ..schemas import GenerateIn, JobOut
from ..billing import check_and_consume_image
from ..jobs.queue import q
from ..jobs.tasks import run_generate
from ..storage import public_url_from_path

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/generate", response_model=JobOut)
def generate(payload: GenerateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ok, limit, used = check_and_consume_image(db, user, 1)
    if not ok:
        raise HTTPException(status_code=402, detail=f"Monthly limit reached ({used}/{limit}). Upgrade needed.")

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

    q.enqueue(run_generate, job.id)

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
