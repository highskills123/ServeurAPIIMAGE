from typing import Optional
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import ImageJob, JobStatus
from ..storage import new_image_path
from ..ai.pipeline import generate_image
from ..jobs.queue import redis_client


def run_generate(job_id: int, cache_key: Optional[str] = None, cache_ttl: int = 86400):
    db: Session = SessionLocal()
    j = None
    try:
        j = db.get(ImageJob, job_id)
        if not j:
            return
        j.status = JobStatus.running
        db.commit()

        out_path = new_image_path(j.user_id)
        generate_image(
            prompt=j.prompt,
            width=j.width,
            height=j.height,
            steps=j.steps,
            guidance=j.guidance,
            out_path=out_path,
        )

        j.status = JobStatus.done
        j.image_path = out_path
        db.commit()

        # Populate prompt cache so identical future requests skip GPU work
        if cache_key:
            redis_client.set(cache_key, out_path, ex=cache_ttl)
    except Exception as e:
        try:
            db.rollback()
            j = db.get(ImageJob, job_id)
            if j:
                j.status = JobStatus.failed
                j.error = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
