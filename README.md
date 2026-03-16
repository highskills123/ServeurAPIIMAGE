# PixelForge AI API

A self-hosted REST API for AI-powered image generation using Stable Diffusion (SDXL-Turbo by default), built with FastAPI, PostgreSQL, Redis, Docker, and Nginx.

![Sample generated image – a futuristic city at sunset](docs/sample_output.png)
*Prompt: "a futuristic city at sunset" — 1024×1024, 4 steps*

---

> 📱 **Mobile & Web client available!**
> The [`mobile/`](mobile/) directory contains a React Native (Expo) app that works as both an **Android app** (Google Play Store) and a **website**. See [mobile/README.md](mobile/README.md) for setup instructions.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Mobile & Web Client](#mobile--web-client)
- [Architecture](#architecture)
- [Plans & Pricing](#plans--pricing)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Rate Limiting](#rate-limiting)
- [GPU & CPU Support](#gpu--cpu-support)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)

---

## What It Does

- **Sign up / log in** and receive a JWT token. New accounts start on the **free** plan (20 images/month).
- **Generate images** from a text prompt. Jobs are queued and processed asynchronously by GPU workers.
- **Poll job status** and get the image URL once generation is complete.
- **Browse pricing plans** and upgrade via Stripe Checkout.
- **Prompt caching** – identical prompts with the same parameters reuse the generated image for 24 hours (no GPU work repeated).

---

## Mobile & Web Client

A ready-to-use client lives in the [`mobile/`](mobile/) directory. It is built with **React Native (Expo)** and runs on:

| Target | How |
|--------|-----|
| 🌐 **Website** | `npm run export:web` → upload `dist/` to Vercel / Netlify / S3 |
| 📱 **Android (Google Play)** | `eas build --platform android` → upload the `.aab` to the Play Console |

See **[mobile/README.md](mobile/README.md)** for full setup and deployment instructions.

---

## Architecture

```
Internet
  │
  ▼
Nginx  (port 80 — reverse proxy, rate limiting, static image serving)
  │
  ▼
FastAPI Backend  ──────────────▶  PostgreSQL  (users, jobs, quotas)
  │ (enqueues jobs)
  ▼
Redis Queue (RQ)  ←── prompt cache (24 h TTL)
  │
  ├──▶ Worker GPU 0  (SDXL-Turbo / Stable Diffusion)
  └──▶ Worker GPU 1  (SDXL-Turbo / Stable Diffusion)
```

| Service | Role |
|---------|------|
| **Nginx** | Reverse proxy on port `80`; per-IP rate limiting; serves images from disk with 7-day cache headers |
| **Backend** (`./backend`) | FastAPI app on port `8000` |
| **Workers** (`./worker`) | RQ workers — one per GPU, pull jobs from Redis and run the AI model |
| **PostgreSQL** | Stores users, image jobs, and quota data |
| **Redis** | Message broker and 24-hour prompt cache |

---

## Plans & Pricing

| Plan     | Price       | Images / month |
|----------|-------------|----------------|
| free     | $0          | 20             |
| starter  | $9 / month  | 300            |
| pro      | $29 / month | 1,000          |
| business | $99 / month | 5,000          |

New accounts are automatically placed on the **free** plan.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) v2+
- NVIDIA GPU(s) with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) *(CPU fallback available for development)*
- Git

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/highskills123/ServeurAPIIMAGE.git
cd ServeurAPIIMAGE
```

### 2. Create your environment file

There is no `.env` file in the repository — you need to create one. An `.env.example` file is provided as a template showing every available variable with safe defaults.

Create your own `.env` by copying the example:

```bash
cp .env.example .env
```

Then open `.env` in your editor and update the values marked below.

#### Full list of variables

```dotenv
# ── Database ──────────────────────────────────────────────────────────────────
POSTGRES_USER=pixelforge          # PostgreSQL username
POSTGRES_PASSWORD=changeme        # ⚠ Change this in production
POSTGRES_DB=pixelforge            # PostgreSQL database name
DATABASE_URL=postgresql+psycopg://pixelforge:changeme@postgres:5432/pixelforge
                                  # ^ Must match the three values above

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Auth ──────────────────────────────────────────────────────────────────────
JWT_SECRET=change_this_super_secret   # ⚠ Use a long random string in production
JWT_EXPIRES_MIN=10080                 # Token lifetime in minutes (default: 7 days)

# ── Storage ───────────────────────────────────────────────────────────────────
DATA_DIR=/data                        # Where generated images are saved inside containers
PUBLIC_BASE_URL=http://localhost      # Public URL used to build image links (no trailing slash)

# ── Stripe (optional — only needed if you want paid plans) ───────────────────
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_STARTER_ID=price_xxx    # Stripe Price ID for the Starter plan
STRIPE_PRICE_PRO_ID=price_xxx        # Stripe Price ID for the Pro plan
STRIPE_PRICE_BUSINESS_ID=price_xxx   # Stripe Price ID for the Business plan

# ── Plan quotas ───────────────────────────────────────────────────────────────
FREE_MONTHLY_LIMIT=20
STARTER_MONTHLY_LIMIT=300
PRO_MONTHLY_LIMIT=1000
BUSINESS_MONTHLY_LIMIT=5000

# ── Rate limiting ─────────────────────────────────────────────────────────────
GENERATE_RATE_LIMIT=20/minute         # SlowAPI syntax: "N/period"

# ── AI model ──────────────────────────────────────────────────────────────────
MODEL_ID=stabilityai/sdxl-turbo       # Any diffusers-compatible text-to-image model
DEFAULT_STEPS=4
DEFAULT_GUIDANCE=0.0
DEFAULT_WIDTH=1024
DEFAULT_HEIGHT=1024
```

> **Minimum required changes before going live:**
> 1. Set a strong `POSTGRES_PASSWORD` and update it in `DATABASE_URL` as well.
> 2. Set a long random `JWT_SECRET` (e.g. `openssl rand -hex 32`).
> 3. Set `PUBLIC_BASE_URL` to your server's public address.
> 4. Fill in `STRIPE_*` values only if you want to accept payments.

### 3. Start the services

```bash
docker compose up --build
```

This starts all services:

| Service | Port |
|---------|------|
| Nginx (entry point) | `80` |
| FastAPI backend | `8000` |
| PostgreSQL | `5432` |
| Redis | `6379` |
| Worker GPU 0 | — |
| Worker GPU 1 | — |

The API is available at **http://localhost** once the stack is ready.

---

## Quick Start

Once the stack is running, generate your first image in three steps.

**Step 1 — Register and get a token:**

```bash
TOKEN=$(curl -s -X POST http://localhost/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

**Step 2 — Submit a generation job:**

```bash
JOB=$(curl -s -X POST http://localhost/images/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a futuristic city at sunset","width":1024,"height":1024,"steps":4,"guidance":0.0}')
JOB_ID=$(echo $JOB | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

**Step 3 — Poll for the result:**

```bash
curl -s http://localhost/images/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"
# {"id":1,"status":"done","image_url":"http://localhost/files/images/1_abc123.png","error":null}
```

Once `status` is `"done"`, open or download `image_url`.

> **Tip:** check the HTTP status code with `curl -s -o /dev/null -w "%{http_code}"` if you get an unexpected response.

---

## API Reference

All authenticated endpoints require `Authorization: Bearer <token>`.

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/signup` | Register a new user. Body: `{ "email": "...", "password": "..." }` |
| `POST` | `/auth/login` | Log in and get a JWT token. Body: `{ "email": "...", "password": "..." }` |
| `GET`  | `/auth/me` | Get the current user's email and plan. |

### Image Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/images/generate` | Submit a generation job. Rate-limited to 20 req/min per IP. |
| `GET`  | `/images/{job_id}` | Get the status and result of a job. |
| `GET`  | `/images/` | List all jobs for the current user. |

**Request body for `POST /images/generate`:**

```json
{
  "prompt": "a futuristic city at sunset",
  "width": 1024,
  "height": 1024,
  "steps": 4,
  "guidance": 0.0
}
```

| Field | Rules |
|-------|-------|
| `prompt` | 3–500 characters |
| `width` / `height` | One of: `256`, `512`, `768`, `1024` |
| `steps` | 1–50 |

**Job response:**

```json
{
  "id": 1,
  "status": "queued",
  "image_url": null,
  "error": null
}
```

`status` values: `queued` → `running` → `done` / `failed`

### Billing

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| `GET`  | `/billing/plans` | No | List all plans with pricing. |
| `POST` | `/billing/checkout` | Yes | Create a Stripe Checkout Session. Body: `{ "plan": "pro", "success_url": "...", "cancel_url": "..." }` |
| `POST` | `/billing/stripe/webhook` | No | Stripe webhook endpoint (signature-verified). |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Returns `{ "ok": true }` when the API is up. |

---

## Rate Limiting

Protection is applied at two independent layers:

| Layer | Rules |
|-------|-------|
| **Nginx** | General API: 20 req/s per IP (burst 40). `/images/generate`: 5 req/s per IP (burst 10). |
| **FastAPI / SlowAPI** | `POST /images/generate`: 20 req/min per IP. |

---

## GPU & CPU Support

The worker automatically picks the best available device at startup:

| Environment | Device | dtype | Notes |
|-------------|--------|-------|-------|
| NVIDIA GPU present | `cuda` | `float16` | Full speed; attention slicing enabled |
| CPU only | `cpu` | `float32` | Development use; ~10–30× slower than GPU |

Set `MODEL_ID` to any `diffusers`-compatible text-to-image model (default: `stabilityai/sdxl-turbo`).

---

## Running Tests

The test suite runs without Docker, PostgreSQL, Redis, or a GPU — it uses SQLite in memory, `fakeredis`, and a stub generator.

```bash
pip install -r backend/requirements-test.txt
cd backend
pytest tests/ -v
```

| Test | Validates |
|------|-----------|
| `test_health_check` | `/health` endpoint |
| `test_signup_creates_user` | User registration |
| `test_login_returns_token` | JWT issued on login |
| `test_duplicate_signup_rejected` | Duplicate email → 400 |
| `test_me_endpoint` | `/auth/me` |
| `test_generate_image_full_flow` | POST → poll → PNG on disk |
| `test_list_jobs` | `GET /images/` |
| `test_generate_prompt_too_short` | Short prompt → 422 |
| `test_generate_invalid_dimensions` | Bad dimensions → 422 |
| `test_generate_requires_auth` | No token → 401 |
| `test_prompt_cache_reuses_image` | Cached image returned |
| `test_monthly_limit_enforced` | Quota exceeded → 402 |

---

## Project Structure

```
ServeurAPIIMAGE/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-test.txt       # Test dependencies (pytest, fakeredis, Pillow, httpx)
│   ├── tests/
│   │   └── test_generate.py        # Integration tests
│   └── app/
│       ├── main.py                 # FastAPI app + SlowAPI setup
│       ├── models.py               # SQLAlchemy models (User, ImageJob, UsageMonthly)
│       ├── schemas.py              # Pydantic schemas + validators
│       ├── auth.py                 # Password hashing & JWT helpers
│       ├── billing.py              # Quota management
│       ├── config.py               # Settings via pydantic-settings
│       ├── db.py                   # Database session
│       ├── deps.py                 # FastAPI dependencies
│       ├── storage.py              # File storage helpers
│       ├── ai/
│       │   └── pipeline.py         # Model loading & inference (GPU/CPU auto-detect)
│       ├── jobs/                   # RQ job definitions, queue & prompt cache
│       └── routes/                 # Route handlers
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py                   # RQ worker entry point
├── nginx/
│   └── nginx.conf                  # Reverse proxy + rate limiting config
├── docs/
│   └── sample_output.png
├── docker-compose.yml
├── .env.example                    # Template — copy to .env and fill in your values
└── README.md
```

---

## License

This project is open source. See the repository for details.
