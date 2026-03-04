from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import ImageJob, JobStatus
from ..storage import new_image_path
from ..ai.pipeline import generate_image


def run_generate(job_id: int):
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
