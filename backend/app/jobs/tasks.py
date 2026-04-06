from typing import Optional
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import ImageJob, JobStatus, JobType
from ..storage import new_image_path
from ..ai.pipeline import generate_image, generate_spritesheet, generate_game_asset
from ..jobs.queue import redis_client


def run_generate(job_id: int, cache_key: Optional[str] = None, cache_ttl: int = 86400, negative_prompt: str = ""):
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
            negative_prompt=negative_prompt,
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


def run_generate_spritesheet(job_id: int, negative_prompt: str = "", style: str = ""):
    """RQ task: generate a sprite sheet and update the job record."""
    db: Session = SessionLocal()
    j = None
    try:
        j = db.get(ImageJob, job_id)
        if not j:
            return
        j.status = JobStatus.running
        db.commit()

        rows = j.rows or 2
        cols = j.cols or 4
        frame_width = j.width // cols
        frame_height = j.height // rows

        out_path = new_image_path(j.user_id)
        generate_spritesheet(
            prompt=j.prompt,
            rows=rows,
            cols=cols,
            frame_width=frame_width,
            frame_height=frame_height,
            steps=j.steps,
            guidance=j.guidance,
            out_path=out_path,
            negative_prompt=negative_prompt,
            style=style,
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


def run_generate_game_asset(job_id: int, asset_type: str, size: str, style: str, negative_prompt: str = ""):
    """RQ task: generate a mobile game or RPG asset and update the job record."""
    db: Session = SessionLocal()
    j = None
    try:
        j = db.get(ImageJob, job_id)
        if not j:
            return
        j.status = JobStatus.running
        db.commit()

        out_path = new_image_path(j.user_id)
        generate_game_asset(
            prompt=j.prompt,
            asset_type=asset_type,
            size=size,
            style=style,
            steps=j.steps,
            guidance=j.guidance,
            out_path=out_path,
            negative_prompt=negative_prompt,
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
