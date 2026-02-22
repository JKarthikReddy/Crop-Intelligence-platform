# Docker — Crop Intelligence Platform

## Purpose

All container configuration files for the Crop Intelligence Platform services.

## Responsibilities

- Service-level Dockerfiles
- Docker Compose orchestration
- Environment-specific overrides
- Container networking configuration

## Does NOT Contain

- Application source code
- Training data
- Environment secrets

## Files

| File | Description |
|------|-------------|
| `backend.Dockerfile` | Backend API service container |
| `frontend.Dockerfile` | Frontend Next.js container |
| `docker-compose.yml` | Multi-service orchestration |

## Usage

```bash
# Build and start all services
docker compose up --build

# Start specific service
docker compose up backend

# Rebuild single service
docker compose build frontend
```

## Ownership

DevOps / Platform Engineering Team
