# ServeurAPIIMAGE

**PixelForge AI API** – A self-hosted REST API server for AI-powered image generation using Stable Diffusion (SDXL-Turbo by default), built with FastAPI, PostgreSQL, Redis, and Docker.

---

## What It Does

ServeurAPIIMAGE provides a complete backend service that lets users:

- **Sign up / log in** and receive a JWT access token.
- **Submit image generation requests** (text-to-image) via a REST endpoint. Each request is queued asynchronously and processed by one or more GPU workers.
- **Poll job status** and retrieve the URL of the generated image once it is ready.
- **List past jobs** and their results.
- **Manage billing quotas** – each user is assigned a plan (Starter / Pro / Business) with a configurable monthly image limit. Stripe webhook support is included for plan upgrades.

### Architecture

```
Client
  │
  ▼
FastAPI Backend  ──────────────▶  PostgreSQL (users, jobs, quotas)
  │ (enqueues jobs)
  ▼
Redis Queue (RQ)
  │
  ├──▶ Worker GPU 0  (runs SDXL-Turbo / Stable Diffusion)
  └──▶ Worker GPU 1  (runs SDXL-Turbo / Stable Diffusion)
```

- **Backend** (`./backend`) – FastAPI application exposing the REST API on port `8000`.
- **Workers** (`./worker`) – RQ workers that pull generation jobs from Redis and run the AI model on GPU. Multiple workers can be deployed (one per GPU).
- **PostgreSQL** – Stores users, image jobs, and quota information.
- **Redis** – Acts as the message broker between the backend and the workers.

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
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_DB` | PostgreSQL database name |
| `DATABASE_URL` | Full SQLAlchemy connection string |
| `REDIS_URL` | Redis connection URL |
| `JWT_SECRET` | Secret key used to sign JWT tokens |
| `JWT_EXPIRES_MIN` | Token expiry in minutes (default: 10080 = 7 days) |
| `DATA_DIR` | Directory where generated images are stored |
| `PUBLIC_BASE_URL` | Public base URL of the API (used to build image URLs) |
| `STRIPE_SECRET_KEY` | Stripe secret key (optional) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret (optional) |
| `STARTER_MONTHLY_LIMIT` | Max images per month for the Starter plan |
| `PRO_MONTHLY_LIMIT` | Max images per month for the Pro plan |
| `BUSINESS_MONTHLY_LIMIT` | Max images per month for the Business plan |
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

---

## API Endpoints

All authenticated endpoints require the `Authorization: Bearer <token>` header.

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/signup` | Register a new user. Body: `{ "email": "...", "password": "..." }` |
| `POST` | `/auth/login` | Log in and get a JWT token. Body: `{ "email": "...", "password": "..." }` |
| `GET`  | `/auth/me` | Get the current user's email and plan. |

### Image Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/images/generate` | Submit a new image generation job. |
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

### Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/billing/stripe/webhook` | Stripe webhook endpoint for plan upgrades. |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Returns `{ "ok": true }` when the API is running. |

---

## Project Structure

```
ServeurAPIIMAGE/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI app entry point
│       ├── models.py        # SQLAlchemy ORM models
│       ├── schemas.py       # Pydantic request/response schemas
│       ├── auth.py          # Password hashing & JWT helpers
│       ├── billing.py       # Quota management
│       ├── config.py        # Settings (pydantic-settings)
│       ├── db.py            # Database session
│       ├── deps.py          # FastAPI dependencies (current user)
│       ├── storage.py       # File storage helpers
│       ├── ai/              # AI model loading & inference
│       ├── jobs/            # RQ job definitions & queue setup
│       └── routes/          # API route handlers
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py            # RQ worker entry point
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## License

This project is open source. See the repository for details.