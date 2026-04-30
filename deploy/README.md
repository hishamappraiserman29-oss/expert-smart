# Expert_Smart — Deployment Package

This folder contains everything needed to run Expert_Smart with **Llama 3** via **Ollama** in **Docker**, locally or on a SaaS provider — without modifying any file under `core_engine/`.

## What's inside

| File | Purpose |
|---|---|
| `Dockerfile.flask` | Container image for the PropTech Flask app (waitress + Python 3.11) |
| `Dockerfile.ollama` | Custom Ollama image that pre-pulls `llama3:8b` and aliases it as `qwen2.5:7b` |
| `docker-compose.yml` | Local development stack: flask + ollama + qdrant |
| `docker-compose.production.yml` | Production overrides (gunicorn, healthchecks, resource limits) |
| `requirements-deploy.txt` | Extra Python deps the deploy stack needs (`ollama`, `gunicorn`, `httpx`) |
| `.env.example` | Environment template — copy to `.env` and fill in |
| `entrypoint.sh` | Flask container startup: env validation + waitress launch |
| `scripts/pull_models.sh` | Ollama init: pulls `llama3:8b` and creates the `qwen2.5:7b` alias |
| `scripts/healthcheck.sh` | Container readiness probe |
| `render.yaml` | Render.com one-click deploy config |
| `fly.toml` | Fly.io deploy config (with persistent Ollama volume) |
| `railway.json` | Railway.app deploy config |
| `nginx.conf` | Reverse proxy with SSL termination (for cloud VMs) |

## How the model swap works (no `core_engine/` changes)

`core_engine/rag_advisor.py:468` calls Ollama with the literal `model="qwen2.5:7b"`. Instead of editing that file, we:

1. Pull the real Llama 3 model: `ollama pull llama3:8b`
2. Create a tag alias: `ollama cp llama3:8b qwen2.5:7b`

This way the existing code requests `qwen2.5:7b` and Ollama transparently serves Llama 3. The alias creation happens automatically in `scripts/pull_models.sh` at first container startup.

To switch to Llama 3 70B (much higher quality, requires more RAM/GPU):
```bash
# Set in .env:
OLLAMA_MODEL=llama3:70b
```

## Quick start (local Docker)

```bash
cd deploy/
cp .env.example .env       # then edit values

# Build & run the full stack
docker compose up -d

# First run: ollama pulls ~5GB for llama3:8b (~3 minutes)
docker compose logs -f ollama

# Once you see "qwen2.5:7b alias ready" the API is up:
curl http://localhost:5000/api/valuation -X POST -H "Content-Type: application/json" \
  -d '{"location":"القاهرة الجديدة","area":250,"property_type":"شقة سكنية"}'
```

## Deploy to SaaS

### Option A — Render.com (easiest)
```bash
# From the repo root:
render blueprint launch deploy/render.yaml
```

### Option B — Fly.io (best for Ollama with persistent volumes)
```bash
fly launch --copy-config --config deploy/fly.toml
fly volumes create ollama_models --size 10
fly deploy
```

### Option C — Railway
```bash
railway up --config deploy/railway.json
```

### Option D — Bare cloud VM (DigitalOcean / AWS EC2 / Azure)
```bash
ssh user@your-server
git clone <your-repo>
cd <your-repo>/deploy/
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

## Resource sizing

| Model | RAM | Disk | Best for |
|---|---|---|---|
| `llama3:8b` | 8 GB | ~5 GB | Default — good quality, runs on small VMs |
| `llama3:70b` | 48 GB+ | ~40 GB | High-quality reports, requires beefy server or GPU |

## Constraint: zero `core_engine/` modifications

Verified — no file under `core_engine/` is read or modified by anything in this folder. The deploy package is fully isolated.
