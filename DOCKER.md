# Docker Setup

This project ships with a Docker setup that runs identically across macOS
(Intel and Apple Silicon), Windows, and Linux. PyTorch is installed from
official prebuilt CPU wheels — no compilation required.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- At least **4GB RAM** allocated to Docker (Settings → Resources)
- At least **10GB free disk space**

---

## File placement

```
oceansense-ai/
|–– docker-compose.yml
|── backend/
|   |–– Dockerfile.backend
|   |–– .dockerignore
|   |–– app/
|   |–– requirements.txt
|   |–– .env
|── frontend/
    |–– Dockerfile.frontend
    |–– .dockerignore
    |–– ...
```

Rename the dockerignore files:

```bash
mv .dockerignore.backend backend/.dockerignore
mv .dockerignore.frontend frontend/.dockerignore
```

---

## Running the project

**First run:**

```bash
docker compose up --build
```

**Subsequent runs:**

```bash
docker compose up
```

**Run in the background:**

```bash
docker compose up -d
```

Once running:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

---

## Retraining the vector store

The ChromaDB store is persisted in a Docker volume so it survives container
restarts. To retrain from scratch:

```bash
# 1. Bring down containers and wipe the volume
docker compose down -v

# 2. Add/remove files in backend/app/datasets/ as needed

# 3. Restart
docker compose up -d

# 4. Trigger reinitialization
curl -X POST http://localhost:8000/initialize
```

---

## Useful commands

```bash
# View live logs from all services
docker compose logs -f

# View backend logs only
docker compose logs -f backend

# Rebuild after changing app code (fast — PyTorch layer is cached)
docker compose up --build

# Stop everything
docker compose down

# Full reset including chroma store volume
docker compose down -v

# Open a shell inside the running backend container
docker compose exec backend bash
```

---

## Next.js standalone output (required)

The frontend Dockerfile uses Next.js's standalone output mode. Make sure
your next.config.ts includes:

```js
const nextConfig: NextConfig = {
  output: 'standalone',
  // ...your existing options
}
```

Without this, the frontend container will fail to start.

---

## Architecture support

| Platform                     | Supported |
| ---------------------------- | --------- |
| macOS Intel (x86_64)         | ✅        |
| macOS Apple Silicon (arm64)  | ✅        |
| Linux x86_64                 | ✅        |
| Linux ARM64                  | ✅        |
| Windows (via Docker Desktop) | ✅        |

PyTorch 2.4.1 CPU wheels are available for both x86_64 and ARM64 on Linux,
so the same image builds and runs correctly on all of the above.

---

## Note on local macOS Intel setup vs Docker

If setting up locally on macOS Intel without Docker, PyTorch must be built
from source — there are no prebuilt macOS Intel wheels for torch>=2.4.0.
See README.md for full local setup instructions. Inside Docker this is not
an issue — containers run Linux, where prebuilt wheels exist for all architectures.
