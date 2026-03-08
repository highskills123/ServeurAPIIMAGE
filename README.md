# ServeurAPIIMAGE

**PixelForge AI API** – A self-hosted REST API server for AI-powered image generation using Stable Diffusion (SDXL-Turbo by default), built with FastAPI, PostgreSQL, Redis, Docker, and Nginx.

---

## What It Does

ServeurAPIIMAGE provides a complete backend service that lets users:

- **Sign up / log in** and receive a JWT access token. New accounts start on the **free** plan (20 images/month).
- **Submit image generation requests** (text-to-image) via a REST endpoint. Each request is queued asynchronously and processed by one or more GPU workers.
- **Poll job status** and retrieve the URL of the generated image once it is ready.
- **List past jobs** and their results.
- **Browse pricing plans** and **purchase a subscription** via Stripe Checkout.
- **Manage billing quotas** – each user is assigned a plan with a configurable monthly image limit. Stripe webhook support handles plan upgrades and cancellations.

### Architecture

```
Internet
  │
  ▼
Nginx (reverse proxy, port 80)  ← rate limiting, static image serving
  │
  ▼
FastAPI Backend  ──────────────▶  PostgreSQL (users, jobs, quotas)
  │ (enqueues jobs)
  ▼
Redis Queue (RQ)  ←── prompt cache (24 h TTL)
  │
  ├──▶ Worker GPU 0  (runs SDXL-Turbo / Stable Diffusion)
  └──▶ Worker GPU 1  (runs SDXL-Turbo / Stable Diffusion)
```

- **Nginx** – Reverse proxy on port 80. Applies per-IP rate limiting (20 req/s general, 5 req/s on `/images/generate`), serves generated images directly from disk with a 7-day cache header.
- **Backend** (`./backend`) – FastAPI application exposing the REST API on port `8000`.
- **Workers** (`./worker`) – RQ workers that pull generation jobs from Redis and run the AI model on GPU. Multiple workers can be deployed (one per GPU).
- **PostgreSQL** – Stores users, image jobs, and quota information.
- **Redis** – Acts as the message broker between the backend and the workers, and as a **prompt cache** (identical prompt+params within 24 h reuse the stored image, skipping GPU work).

---

## Plans & Pricing

| Plan     | Price       | Images / month |
|----------|-------------|----------------|
| free     | $0          | 20             |
| starter  | $9 / month  | 300            |
| pro      | $29 / month | 1 000          |
| business | $99 / month | 5 000          |

New accounts start on the **free** plan automatically.
Call `GET /billing/plans` to retrieve the current plan list at runtime.
Call `POST /billing/checkout` (authenticated) to create a Stripe Checkout Session.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) v2+
- NVIDIA GPU(s) with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed (required for the GPU workers)
- Git

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/highskills123/ServeurAPIIMAGE.git
cd ServeurAPIIMAGE
```

### 2. Configure environment variables

Copy the example environment file and edit the values:

```bash
cp .env.example .env
```

Key variables to update:

| Variable | Description |
|---|---|
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password (change in production) |
| `POSTGRES_DB` | PostgreSQL database name |
| `DATABASE_URL` | Full SQLAlchemy connection string |
| `REDIS_URL` | Redis connection URL |
| `JWT_SECRET` | Secret key used to sign JWT tokens |
| `JWT_EXPIRES_MIN` | Token expiry in minutes (default: 10080 = 7 days) |
| `DATA_DIR` | Directory where generated images are stored |
| `PUBLIC_BASE_URL` | Public base URL of the API (used to build image URLs) |
| `STRIPE_SECRET_KEY` | Stripe secret key (optional) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret (optional) |
| `STRIPE_PRICE_STARTER_ID` | Stripe Price ID for the Starter plan |
| `STRIPE_PRICE_PRO_ID` | Stripe Price ID for the Pro plan |
| `STRIPE_PRICE_BUSINESS_ID` | Stripe Price ID for the Business plan |
| `FREE_MONTHLY_LIMIT` | Max images per month for the Free plan (default: 20) |
| `STARTER_MONTHLY_LIMIT` | Max images per month for the Starter plan (default: 300) |
| `PRO_MONTHLY_LIMIT` | Max images per month for the Pro plan (default: 1000) |
| `BUSINESS_MONTHLY_LIMIT` | Max images per month for the Business plan (default: 5000) |
| `MODEL_ID` | Hugging Face model ID (default: `stabilityai/sdxl-turbo`) |
| `DEFAULT_STEPS` | Default number of inference steps |
| `DEFAULT_GUIDANCE` | Default guidance scale |
| `DEFAULT_WIDTH` | Default image width in pixels |
| `DEFAULT_HEIGHT` | Default image height in pixels |

### 3. Start the services

```bash
docker compose up --build
```

This starts:
- PostgreSQL on port `5432`
- Redis on port `6379`
- FastAPI backend on port `8000`
- Two GPU workers (`worker_gpu0` on GPU 0, `worker_gpu1` on GPU 1)
- **Nginx** on port `80` (reverse proxy + rate limiter)

---

## API Endpoints

All authenticated endpoints require the `Authorization: Bearer <token>` header.

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/signup` | Register a new user (starts on the **free** plan). Body: `{ "email": "...", "password": "..." }` |
| `POST` | `/auth/login` | Log in and get a JWT token. Body: `{ "email": "...", "password": "..." }` |
| `GET`  | `/auth/me` | Get the current user's email and plan. |

### Image Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/images/generate` | Submit a new image generation job. **Rate-limited to 20 req/min per IP.** |
| `GET`  | `/images/{job_id}` | Get the status and result of a job. |
| `GET`  | `/images/` | List all jobs for the authenticated user. |

**Generate request body:**

```json
{
  "prompt": "a futuristic city at sunset",
  "width": 1024,
  "height": 1024,
  "steps": 4,
  "guidance": 0.0
}
```

Validation rules:
- `prompt`: 3–500 characters (stripped)
- `width` / `height`: must be one of `256`, `512`, `768`, `1024`
- `steps`: 1–50

**Job response:**

```json
{
  "id": 1,
  "status": "queued",
  "image_url": null,
  "error": null
}
```

`status` can be `queued`, `running`, `done`, or `failed`.
Once `status` is `done`, `image_url` contains the full URL to the generated image.

> **Prompt cache:** if the exact same `prompt` + dimensions + steps + guidance has been generated in the last 24 hours, the stored image is returned immediately (no GPU work queued).

### Billing

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET`  | `/billing/plans` | No | List all available plans with pricing. |
| `POST` | `/billing/checkout` | Yes | Create a Stripe Checkout Session to upgrade your plan. |
| `POST` | `/billing/stripe/webhook` | No | Stripe webhook (signature-verified). |

**Checkout request body:**

```json
{
  "plan": "pro",
  "success_url": "https://yourapp.com/success",
  "cancel_url": "https://yourapp.com/cancel"
}
```

Returns `{ "checkout_url": "...", "session_id": "..." }`. Redirect the user to `checkout_url`.

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Returns `{ "ok": true }` when the API is running. |

---

## Anti-Abuse & Rate Limiting

Protection is applied at two layers:

1. **Nginx** (network layer) – `limit_req_zone` zones:
   - General API: 20 req/s per IP with burst of 40.
   - `/images/generate`: 5 req/s per IP with burst of 10.

2. **FastAPI / SlowAPI** (application layer) – `@limiter.limit("20/minute")` on `POST /images/generate` (independent per-IP enforcement).

3. **Input validation** – Pydantic validators reject prompts shorter than 3 chars or longer than 500 chars, invalid dimensions, or out-of-range step counts before any GPU work is queued.

---

## Project Structure

```
ServeurAPIIMAGE/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI app + SlowAPI rate limiter setup
│       ├── models.py        # SQLAlchemy ORM models (User, ImageJob, UsageMonthly)
│       ├── schemas.py       # Pydantic request/response schemas + validators
│       ├── auth.py          # Password hashing & JWT helpers
│       ├── billing.py       # Quota management (all four plans)
│       ├── config.py        # Settings (pydantic-settings)
│       ├── db.py            # Database session
│       ├── deps.py          # FastAPI dependencies (current user)
│       ├── storage.py       # File storage helpers
│       ├── ai/              # AI model loading & inference
│       ├── jobs/            # RQ job definitions, queue setup & prompt cache
│       └── routes/          # API route handlers
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py            # RQ worker entry point
├── nginx/
│   └── nginx.conf           # Nginx reverse proxy + rate limiting config
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## License

This project is open source. See the repository for details.
