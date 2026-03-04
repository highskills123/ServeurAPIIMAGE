import os
import uuid
from .config import settings


def ensure_dirs():
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.DATA_DIR, "images"), exist_ok=True)


def new_image_path(user_id: int) -> str:
    ensure_dirs()
    fn = f"{user_id}_{uuid.uuid4().hex}.png"
    return os.path.join(settings.DATA_DIR, "images", fn)


def public_url_from_path(path: str) -> str:
    # /data/images/xxx.png -> /files/images/xxx.png
    base = os.path.basename(path)
    return f"{settings.PUBLIC_BASE_URL}/files/images/{base}"
