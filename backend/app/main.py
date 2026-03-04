import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .db import Base, engine
from .storage import ensure_dirs
from .routes.auth_routes import router as auth_router
from .routes.image_routes import router as image_router
from .routes.billing_routes import router as billing_router
from .config import settings

app = FastAPI(title="PixelForge AI API")

Base.metadata.create_all(bind=engine)
ensure_dirs()

# Servir les images générées
images_dir = os.path.join(settings.DATA_DIR, "images")
os.makedirs(images_dir, exist_ok=True)
app.mount("/files/images", StaticFiles(directory=images_dir), name="images")

app.include_router(auth_router)
app.include_router(image_router)
app.include_router(billing_router)


@app.get("/health")
def health():
    return {"ok": True}
