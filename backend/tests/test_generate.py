"""
Integration tests for image generation.

These tests exercise the full HTTP flow (sign-up → POST /images/generate →
GET /images/{job_id}) without touching real PostgreSQL, Redis, or GPU hardware:

  - SQLite in-memory replaces PostgreSQL.
  - fakeredis replaces the real Redis / RQ connection.
  - A stub replaces the heavy torch/diffusers pipeline.
  - Jobs are executed synchronously (inline) instead of via an RQ worker.
"""
import os
import sys
import tempfile

# ── Environment variables must be set BEFORE any app module is imported ────────
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-tests-only")
os.environ.setdefault("DATA_DIR", os.path.join(tempfile.gettempdir(), "pixelforge-test"))
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")

# Ensure the backend/ directory is on sys.path so 'app' is importable
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import pytest
from unittest.mock import patch, MagicMock

import fakeredis
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.config import settings as _settings

# ── Shared in-memory SQLite database (StaticPool = single shared connection) ───
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def _override_get_db():
    """FastAPI dependency override: use the SQLite test session."""
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


# ── Stub AI pipeline ───────────────────────────────────────────────────────────

def _fake_generate_image(prompt: str, width: int, height: int,
                         steps: int, guidance: float, out_path: str,
                         negative_prompt: str = "") -> str:
    """Creates a solid-colour PNG without loading torch or any AI model."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img = Image.new("RGB", (width, height), color=(73, 109, 137))
    img.save(out_path)
    return out_path


def _fake_generate_spritesheet(
    prompt: str,
    rows: int,
    cols: int,
    frame_width: int,
    frame_height: int,
    steps: int,
    guidance: float,
    out_path: str,
    negative_prompt: str = "",
    style: str = "",
) -> str:
    """Creates a solid-colour sprite sheet PNG without loading any AI model."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet = Image.new("RGBA", (cols * frame_width, rows * frame_height), color=(100, 149, 237, 255))
    sheet.save(out_path, format="PNG")
    return out_path


def _fake_generate_game_asset(
    prompt: str,
    asset_type: str,
    size: str,
    style: str,
    steps: int,
    guidance: float,
    out_path: str,
    negative_prompt: str = "",
) -> str:
    """Creates a solid-colour game asset PNG without loading any AI model."""
    from app.ai.pipeline import _ASSET_DIMENSIONS
    dims = _ASSET_DIMENSIONS.get(asset_type, {}).get(size, (512, 512))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img = Image.new("RGB", dims, color=(200, 100, 50))
    img.save(out_path)
    return out_path


# ── pytest fixture ─────────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path):
    """
    Provides a TestClient wired to:
      - an in-memory SQLite database (instead of PostgreSQL)
      - fakeredis (instead of real Redis)
      - a stub image generator (instead of the real AI model)
      - synchronous job execution (instead of the RQ worker process)
    """
    Base.metadata.create_all(bind=_engine)

    data_dir = str(tmp_path)
    os.makedirs(os.path.join(data_dir, "images"), exist_ok=True)

    fake_redis = fakeredis.FakeRedis()

    def _sync_enqueue(func, *args, **kwargs):
        """Run the RQ job inline (synchronously) so tests don't need a worker."""
        with patch("app.jobs.tasks.SessionLocal", _TestSession), \
             patch.object(_settings, "DATA_DIR", data_dir):
            func(*args, **kwargs)
        mock_job = MagicMock()
        mock_job.id = "sync-test-job"
        return mock_job

    app.dependency_overrides[get_db] = _override_get_db

    with patch("app.jobs.queue.redis_client", fake_redis), \
         patch("app.routes.image_routes.redis_client", fake_redis), \
         patch("app.jobs.tasks.redis_client", fake_redis), \
         patch("app.jobs.queue.q.enqueue", side_effect=_sync_enqueue), \
         patch("app.jobs.tasks.generate_image", side_effect=_fake_generate_image), \
         patch("app.jobs.tasks.generate_spritesheet", side_effect=_fake_generate_spritesheet), \
         patch("app.jobs.tasks.generate_game_asset", side_effect=_fake_generate_game_asset), \
         patch.object(_settings, "DATA_DIR", data_dir):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=_engine)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _signup_and_login(client: TestClient, email: str = "user@example.com",
                      password: str = "secret123") -> str:
    """Register a user and return the JWT bearer token."""
    r = client.post("/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_signup_creates_user(client):
    r = client.post("/auth/signup",
                    json={"email": "new@example.com", "password": "pass1234"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_returns_token(client):
    token = _signup_and_login(client, "login@example.com", "mypassword")
    assert isinstance(token, str) and len(token) > 10


def test_duplicate_signup_rejected(client):
    _signup_and_login(client, "dup@example.com", "pw")
    r = client.post("/auth/signup",
                    json={"email": "dup@example.com", "password": "pw"})
    assert r.status_code == 400


def test_me_endpoint(client):
    token = _signup_and_login(client, "me@example.com", "pw123456")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "me@example.com"
    assert data["plan"] == "free"


def test_generate_image_full_flow(client, tmp_path):
    """
    End-to-end test: sign up → submit a generation request → poll job status →
    verify the job completes and the image file actually exists on disk.
    """
    token = _signup_and_login(client, "gen@example.com", "genpass1")
    headers = {"Authorization": f"Bearer {token}"}

    # Submit a generation job
    payload = {
        "prompt": "a futuristic city at sunset",
        "width": 512,
        "height": 512,
        "steps": 1,
        "guidance": 0.0,
    }
    r = client.post("/images/generate", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    job_data = r.json()
    assert "id" in job_data
    assert job_data["job_type"] == "image"

    # POST /images/generate always returns "queued" immediately (async design).
    # Because _sync_enqueue runs the job inline, the job is already processed by
    # the time we poll GET /images/{id}.
    job_id = job_data["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.status_code == 200
    job_data2 = r2.json()

    assert job_data2["status"] == "done", (
        f"Expected status 'done' but got '{job_data2['status']}'. "
        f"Error: {job_data2.get('error')}"
    )

    # The response must include an image URL
    image_url = job_data2.get("image_url")
    assert image_url is not None, "image_url should not be None when status is done"
    assert image_url.startswith("http"), f"Unexpected image_url: {image_url}"

    # Confirm the PNG was written to disk
    filename = image_url.split("/")[-1]
    data_dir = str(tmp_path)
    image_file = os.path.join(data_dir, "images", filename)
    assert os.path.isfile(image_file), f"PNG not found at {image_file}"

    img = Image.open(image_file)
    assert img.size == (512, 512)
    assert img.mode == "RGB"


def test_list_jobs(client):
    """GET /images/ returns all jobs for the authenticated user."""
    token = _signup_and_login(client, "list@example.com", "listpass1")
    headers = {"Authorization": f"Bearer {token}"}

    # Generate two images
    for _ in range(2):
        client.post("/images/generate",
                    json={"prompt": "test prompt abc", "width": 256,
                          "height": 256, "steps": 1, "guidance": 0.0},
                    headers=headers)

    r = client.get("/images/", headers=headers)
    assert r.status_code == 200
    jobs = r.json()
    assert len(jobs) == 2
    for j in jobs:
        assert j["status"] == "done"


def test_generate_prompt_too_short(client):
    token = _signup_and_login(client, "val@example.com", "valpass1")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/images/generate",
                    json={"prompt": "ab", "width": 512, "height": 512,
                          "steps": 1, "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 422


def test_generate_invalid_dimensions(client):
    token = _signup_and_login(client, "dim@example.com", "dimpass1")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/images/generate",
                    json={"prompt": "valid prompt here", "width": 300,
                          "height": 512, "steps": 1, "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 422


def test_generate_requires_auth(client):
    r = client.post("/images/generate",
                    json={"prompt": "no auth test", "width": 512,
                          "height": 512, "steps": 1, "guidance": 0.0})
    assert r.status_code == 401


def test_prompt_cache_reuses_image(client):
    """
    Generating the same prompt+params twice should reuse the cached image
    (no second AI call) and both jobs should reference the same image path.
    """
    token = _signup_and_login(client, "cache@example.com", "cachepass1")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"prompt": "a red apple on a table", "width": 256,
               "height": 256, "steps": 1, "guidance": 0.0}

    # First request – queued and processed inline by _sync_enqueue
    r1 = client.post("/images/generate", json=payload, headers=headers)
    assert r1.status_code == 200
    job_id1 = r1.json()["id"]

    # Poll to get the actual image_url after processing
    r1_poll = client.get(f"/images/{job_id1}", headers=headers)
    assert r1_poll.json()["status"] == "done"
    url1 = r1_poll.json()["image_url"]
    assert url1 is not None

    # Second request with identical prompt+params – must be a cache hit.
    # The cache-hit branch sets image_url in the POST response directly.
    r2 = client.post("/images/generate", json=payload, headers=headers)
    assert r2.status_code == 200
    url2 = r2.json()["image_url"]

    # Both requests should return the same image URL (served from cache)
    assert url1 == url2, "Prompt cache should return the same image URL"


def test_monthly_limit_enforced(client):
    """Users on the free plan cannot exceed FREE_MONTHLY_LIMIT images."""
    # Use a very small limit so we stay well under the 20/minute rate limiter
    small_limit = 3

    with patch.object(_settings, "FREE_MONTHLY_LIMIT", small_limit):
        token = _signup_and_login(client, "limit@example.com", "limitpass1")
        headers = {"Authorization": f"Bearer {token}"}

        # Use unique prompts so each request counts against the monthly quota
        def _make_payload(i: int) -> dict:
            return {"prompt": f"mountain landscape variant {i}", "width": 256,
                    "height": 256, "steps": 1, "guidance": 0.0}

        for i in range(small_limit):
            r = client.post("/images/generate", json=_make_payload(i), headers=headers)
            assert r.status_code == 200, (
                f"Request {i + 1} failed with {r.status_code}: {r.text}"
            )

        # The next request must be rejected with 402
        r_over = client.post("/images/generate",
                             json=_make_payload(small_limit), headers=headers)
        assert r_over.status_code == 402, (
            f"Expected 402 after exceeding monthly limit, got {r_over.status_code}"
        )


# ── Sprite sheet tests ─────────────────────────────────────────────────────────

def test_spritesheet_full_flow(client, tmp_path):
    """End-to-end test for sprite sheet generation: 2×4 grid of 128×128 frames."""
    token = _signup_and_login(client, "sheet@example.com", "sheetpass1")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "prompt": "running knight character animation",
        "rows": 2,
        "cols": 4,
        "frame_width": 128,
        "frame_height": 128,
        "steps": 1,
        "guidance": 0.0,
    }
    r = client.post("/images/spritesheet", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    job_data = r.json()
    assert job_data["job_type"] == "spritesheet"

    job_id = job_data["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.status_code == 200
    job_data2 = r2.json()
    assert job_data2["status"] == "done", f"Error: {job_data2.get('error')}"

    image_url = job_data2["image_url"]
    assert image_url is not None

    # Verify the sprite sheet dimensions: cols*frame_width × rows*frame_height
    filename = image_url.split("/")[-1]
    image_file = os.path.join(str(tmp_path), "images", filename)
    assert os.path.isfile(image_file), f"Sprite sheet not found at {image_file}"

    img = Image.open(image_file)
    assert img.size == (4 * 128, 2 * 128), f"Unexpected size: {img.size}"


def test_spritesheet_requires_auth(client):
    r = client.post("/images/spritesheet",
                    json={"prompt": "warrior", "rows": 1, "cols": 2,
                          "frame_width": 64, "frame_height": 64,
                          "steps": 1, "guidance": 0.0})
    assert r.status_code == 401


def test_spritesheet_invalid_rows(client):
    """rows must be between 1 and 8."""
    token = _signup_and_login(client, "sval@example.com", "svalpass1")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/images/spritesheet",
                    json={"prompt": "knight", "rows": 0, "cols": 2,
                          "frame_width": 128, "frame_height": 128,
                          "steps": 1, "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 422


def test_spritesheet_invalid_frame_size(client):
    """frame_width must be one of 64, 128, 256."""
    token = _signup_and_login(client, "sfr@example.com", "sfrpass1")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/images/spritesheet",
                    json={"prompt": "knight", "rows": 1, "cols": 2,
                          "frame_width": 100, "frame_height": 128,
                          "steps": 1, "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 422


def test_spritesheet_quota_counts_frames(client):
    """A 2×3 sprite sheet should consume 6 images from the monthly quota."""
    small_limit = 5  # Fewer than the 6 frames the sheet requires

    with patch.object(_settings, "FREE_MONTHLY_LIMIT", small_limit):
        token = _signup_and_login(client, "squo@example.com", "squopass1")
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/images/spritesheet",
                        json={"prompt": "goblin walk cycle", "rows": 2, "cols": 3,
                              "frame_width": 64, "frame_height": 64,
                              "steps": 1, "guidance": 0.0},
                        headers=headers)
        assert r.status_code == 402, (
            f"Expected 402 because 6 frames > limit of {small_limit}, got {r.status_code}"
        )


# ── Game asset tests ───────────────────────────────────────────────────────────

def test_game_asset_character_full_flow(client, tmp_path):
    """End-to-end test: generate a medium character game asset."""
    token = _signup_and_login(client, "asset@example.com", "assetpass1")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "prompt": "brave knight with sword and shield",
        "asset_type": "character",
        "size": "medium",
        "style": "cartoon",
        "steps": 1,
        "guidance": 0.0,
    }
    r = client.post("/images/game-asset", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    job_data = r.json()
    assert job_data["job_type"] == "game_asset"

    job_id = job_data["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.status_code == 200
    job_data2 = r2.json()
    assert job_data2["status"] == "done", f"Error: {job_data2.get('error')}"

    image_url = job_data2["image_url"]
    assert image_url is not None

    filename = image_url.split("/")[-1]
    image_file = os.path.join(str(tmp_path), "images", filename)
    assert os.path.isfile(image_file), f"Game asset PNG not found at {image_file}"

    img = Image.open(image_file)
    # medium character → 512×512
    assert img.size == (512, 512), f"Unexpected size: {img.size}"


def test_game_asset_all_types_accepted(client):
    """All defined asset types (original + RPG) should be accepted by the endpoint."""
    token = _signup_and_login(client, "alltype@example.com", "alltypepass1")
    headers = {"Authorization": f"Bearer {token}"}

    all_types = (
        # Original types
        "character", "item", "background", "icon", "ui_element",
        # RPG types
        "hero", "enemy", "npc", "map_tile", "weapon", "armor", "boss", "portrait",
    )
    for asset_type in all_types:
        r = client.post("/images/game-asset",
                        json={"prompt": "test asset for game",
                              "asset_type": asset_type,
                              "size": "small",
                              "style": "pixel art",
                              "steps": 1,
                              "guidance": 0.0},
                        headers=headers)
        assert r.status_code == 200, f"Failed for asset_type={asset_type}: {r.text}"
        assert r.json()["job_type"] == "game_asset"


def test_game_asset_invalid_type(client):
    """Unknown asset_type should be rejected with 422."""
    token = _signup_and_login(client, "invtype@example.com", "invtypepass1")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/images/game-asset",
                    json={"prompt": "test", "asset_type": "dragon",
                          "size": "medium", "steps": 1, "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 422


def test_game_asset_requires_auth(client):
    r = client.post("/images/game-asset",
                    json={"prompt": "coin sprite", "asset_type": "item",
                          "size": "small", "steps": 1, "guidance": 0.0})
    assert r.status_code == 401


def test_game_asset_style_too_long(client):
    """style must not exceed 100 characters."""
    token = _signup_and_login(client, "stylelen@example.com", "stylelenpass1")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/images/game-asset",
                    json={"prompt": "coin", "asset_type": "item", "size": "small",
                          "style": "x" * 101, "steps": 1, "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 422


# ── RPG asset tests ────────────────────────────────────────────────────────────

def test_rpg_hero_asset(client, tmp_path):
    """RPG hero asset is generated at the correct dimensions (medium → 512×512)."""
    token = _signup_and_login(client, "rpghero@example.com", "rpgheropass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/game-asset",
                    json={"prompt": "brave warrior with glowing sword",
                          "asset_type": "hero",
                          "size": "medium",
                          "style": "pixel art RPG",
                          "steps": 1,
                          "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["job_type"] == "game_asset"

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done", f"Error: {r2.json().get('error')}"

    filename = r2.json()["image_url"].split("/")[-1]
    img = Image.open(os.path.join(str(tmp_path), "images", filename))
    assert img.size == (512, 512), f"Unexpected hero size: {img.size}"


def test_rpg_enemy_asset(client, tmp_path):
    """RPG enemy asset is generated at the correct dimensions (large → 1024×1024)."""
    token = _signup_and_login(client, "rpgenemy@example.com", "rpgenemypass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/game-asset",
                    json={"prompt": "fire-breathing dragon monster",
                          "asset_type": "enemy",
                          "size": "large",
                          "style": "2D pixel art",
                          "steps": 1,
                          "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 200, r.text

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done"

    filename = r2.json()["image_url"].split("/")[-1]
    img = Image.open(os.path.join(str(tmp_path), "images", filename))
    assert img.size == (1024, 1024), f"Unexpected enemy size: {img.size}"


def test_rpg_boss_asset_small(client, tmp_path):
    """RPG boss smallest tier still starts at 512×512."""
    token = _signup_and_login(client, "rpgboss@example.com", "rpgbosspass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/game-asset",
                    json={"prompt": "dark overlord in black armour",
                          "asset_type": "boss",
                          "size": "small",
                          "style": "2D pixel art",
                          "steps": 1,
                          "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 200, r.text

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done"

    filename = r2.json()["image_url"].split("/")[-1]
    img = Image.open(os.path.join(str(tmp_path), "images", filename))
    assert img.size == (512, 512), f"Unexpected boss size: {img.size}"


def test_rpg_map_tile_asset(client, tmp_path):
    """RPG map tile is generated and returned successfully."""
    token = _signup_and_login(client, "rpgmap@example.com", "rpgmappass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/game-asset",
                    json={"prompt": "stone dungeon floor tile",
                          "asset_type": "map_tile",
                          "size": "small",
                          "style": "2D pixel art top-down",
                          "steps": 1,
                          "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 200, r.text

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done"

    filename = r2.json()["image_url"].split("/")[-1]
    img = Image.open(os.path.join(str(tmp_path), "images", filename))
    assert img.size == (256, 256), f"Unexpected map_tile size: {img.size}"


def test_rpg_portrait_asset(client, tmp_path):
    """RPG portrait asset is generated at the correct medium dimensions (512×512)."""
    token = _signup_and_login(client, "rpgport@example.com", "rpgportpass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/game-asset",
                    json={"prompt": "elderly wizard with long white beard",
                          "asset_type": "portrait",
                          "size": "medium",
                          "style": "painterly illustration",
                          "steps": 1,
                          "guidance": 0.0},
                    headers=headers)
    assert r.status_code == 200, r.text

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done"

    filename = r2.json()["image_url"].split("/")[-1]
    img = Image.open(os.path.join(str(tmp_path), "images", filename))
    assert img.size == (512, 512), f"Unexpected portrait size: {img.size}"


# ── negative_prompt tests ──────────────────────────────────────────────────────

def test_generate_with_negative_prompt(client, tmp_path):
    """Supplying a negative_prompt is accepted and the job completes successfully."""
    token = _signup_and_login(client, "negprompt@example.com", "negpromptpass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/generate",
                    json={"prompt": "enchanted forest at dawn",
                          "width": 256,
                          "height": 256,
                          "steps": 1,
                          "guidance": 0.0,
                          "negative_prompt": "blurry, low quality"},
                    headers=headers)
    assert r.status_code == 200, r.text

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done"


def test_generate_negative_prompt_too_long(client):
    """negative_prompt exceeding 300 characters should be rejected with 422."""
    token = _signup_and_login(client, "neglong@example.com", "neglongpass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/generate",
                    json={"prompt": "a castle on a hill",
                          "width": 256,
                          "height": 256,
                          "steps": 1,
                          "guidance": 0.0,
                          "negative_prompt": "x" * 301},
                    headers=headers)
    assert r.status_code == 422


def test_spritesheet_with_negative_prompt(client, tmp_path):
    """Sprite sheet generation accepts and uses a custom negative_prompt."""
    token = _signup_and_login(client, "sneg@example.com", "snegpass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/spritesheet",
                    json={"prompt": "RPG hero walk cycle",
                          "rows": 1,
                          "cols": 4,
                          "frame_width": 64,
                          "frame_height": 64,
                          "steps": 1,
                          "guidance": 0.0,
                          "negative_prompt": "blurry, deformed"},
                    headers=headers)
    assert r.status_code == 200, r.text

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done"


def test_game_asset_with_negative_prompt(client, tmp_path):
    """Game asset generation accepts and uses a custom negative_prompt."""
    token = _signup_and_login(client, "ganeg@example.com", "ganegpass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/game-asset",
                    json={"prompt": "goblin archer",
                          "asset_type": "enemy",
                          "size": "small",
                          "style": "pixel art",
                          "steps": 1,
                          "guidance": 0.0,
                          "negative_prompt": "blurry, ugly"},
                    headers=headers)
    assert r.status_code == 200, r.text

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done"


def test_rpg_asset_dimensions_table(client):
    """All RPG asset types have correct dimension entries in the pipeline table."""
    from app.ai.pipeline import _ASSET_DIMENSIONS, _ASSET_PROMPT_PREFIXES

    rpg_types = ("hero", "enemy", "npc", "map_tile", "weapon", "armor", "boss", "portrait")
    for atype in rpg_types:
        assert atype in _ASSET_DIMENSIONS, f"Missing dimensions for {atype}"
        assert atype in _ASSET_PROMPT_PREFIXES, f"Missing prompt prefix for {atype}"
        for size in ("small", "medium", "large"):
            assert size in _ASSET_DIMENSIONS[atype], f"Missing size '{size}' for {atype}"
            w, h = _ASSET_DIMENSIONS[atype][size]
            assert w >= 256 and h >= 256, f"{atype}/{size} dimensions too small: {w}×{h}"


# ── Spritesheet style tests ────────────────────────────────────────────────────

def test_spritesheet_with_style(client, tmp_path):
    """Sprite sheet generation accepts a style field and completes successfully."""
    token = _signup_and_login(client, "sstyle@example.com", "sstylepass1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/images/spritesheet",
                    json={"prompt": "dark knight walking animation",
                          "rows": 1,
                          "cols": 4,
                          "frame_width": 64,
                          "frame_height": 64,
                          "steps": 1,
                          "guidance": 0.0,
                          "style": "dark_gothic_rpg"},
                    headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["job_type"] == "spritesheet"

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done", f"Error: {r2.json().get('error')}"


def test_spritesheet_dark_gothic_rpg_preset(client, tmp_path):
    """Dark gothic RPG preset produces a valid sprite sheet at correct dimensions."""
    token = _signup_and_login(client, "gothic@example.com", "gothicpass1")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "prompt": "undead warrior with cursed sword",
        "rows": 2,
        "cols": 4,
        "frame_width": 128,
        "frame_height": 128,
        "steps": 1,
        "guidance": 0.0,
        "style": "dark_gothic_rpg",
        "negative_prompt": "bright colors, anime, cartoon",
    }
    r = client.post("/images/spritesheet", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["job_type"] == "spritesheet"

    job_id = r.json()["id"]
    r2 = client.get(f"/images/{job_id}", headers=headers)
    assert r2.json()["status"] == "done", f"Error: {r2.json().get('error')}"

    image_url = r2.json()["image_url"]
    assert image_url is not None

    filename = image_url.split("/")[-1]
    image_file = os.path.join(str(tmp_path), "images", filename)
    assert os.path.isfile(image_file), f"Dark gothic sprite sheet not found at {image_file}"

    img = Image.open(image_file)
    assert img.size == (4 * 128, 2 * 128), f"Unexpected dark gothic sheet size: {img.size}"


def test_spritesheet_style_too_long(client):
    """style field must not exceed 100 characters."""
    token = _signup_and_login(client, "slong@example.com", "slongpass1")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/images/spritesheet",
                    json={"prompt": "knight", "rows": 1, "cols": 2,
                          "frame_width": 64, "frame_height": 64,
                          "steps": 1, "guidance": 0.0,
                          "style": "x" * 101},
                    headers=headers)
    assert r.status_code == 422


def test_spritesheet_style_table(client):
    """Dark gothic RPG style prefix is registered in the pipeline table."""
    from app.ai.pipeline import _SPRITESHEET_STYLE_PREFIXES, _SPRITESHEET_BASE_CONTEXT

    assert "dark_gothic_rpg" in _SPRITESHEET_STYLE_PREFIXES, \
        "dark_gothic_rpg must be in the spritesheet style prefix table"
    prefix = _SPRITESHEET_STYLE_PREFIXES["dark_gothic_rpg"]
    assert len(prefix) > 10, "dark_gothic_rpg prefix should be a meaningful description"

    assert _SPRITESHEET_BASE_CONTEXT, "Base sprite-sheet context must be non-empty"
    assert "sprite sheet" in _SPRITESHEET_BASE_CONTEXT.lower() or \
           "animation" in _SPRITESHEET_BASE_CONTEXT.lower(), \
        "Base context should reference sprite sheet or animation"
