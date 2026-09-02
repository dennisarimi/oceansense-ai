# OceanSense AI

A RAG-based oceanographic AI chatbot built with FastAPI, PyTorch, ChromaDB, Ollama (Mistral 7B), and Next.js.

---

## Project Structure

```
oceansense-ai/
├── backend/
│   ├── app/
│   │   ├── datasets/         # Source documents for RAG
│   │   ├── chroma_store/     # Vector store (generated, not committed)
│   │   ├── main.py
│   │   ├── rag_pipeline.py
│   │   ├── chroma_utils.py
│   │   └── mistral_utils.py
│   ├── pytorch/              # PyTorch source (local macOS Intel only, not committed)
│   ├── venv/                 # Virtual environment (not committed)
│   ├── requirements.txt
│   ├── Dockerfile.backend
│   └── .env
├── frontend/
│   ├── Dockerfile.frontend
│   └── ...                   # Standard Next.js project structure
├── docker-compose.yml
├── compose.sh                # Optional compose wrapper
└── run                       # Code Ocean reproducibility script
```

---

## Quick Start (Docker — recommended)

The easiest way to run this project on any machine. See [Docker Setup](#docker-setup) below.

```bash
# Production
docker compose up --build

# Development (hot reload)
NODE_ENV=dev docker compose up --build
```

---

## Docker Setup

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- At least 8GB RAM allocated to Docker (Settings → Resources)
- At least 10GB free disk space
- Project directory must **not** be inside iCloud Drive (causes Docker mount failures)
  - Recommended location: `~/Developer/oceansense-ai`

### File placement
Rename and place Docker ignore files as follows:
```bash
mv .dockerignore.backend backend/.dockerignore
mv .dockerignore.frontend frontend/.dockerignore
```

### Running

```bash
# First run (builds images, pulls Mistral ~4GB — takes several minutes)
docker compose up --build

# Subsequent runs
docker compose up

# Development mode (hot reload on both frontend and backend)
NODE_ENV=dev docker compose up --build

# Background
docker compose up -d
```

Once running:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### How dev/prod switching works
`NODE_ENV=dev` selects the `dev` build stage in both Dockerfiles, which:
- Runs uvicorn with `--reload` on the backend
- Runs `next dev` on the frontend
- Only the exact value `dev` triggers this — anything else defaults to prod

### Next.js standalone output (required for prod)
Make sure `next.config.ts` includes:
```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
}

export default nextConfig
```

### Useful commands
```bash
docker compose logs -f                  # live logs all services
docker compose logs -f backend          # backend only
docker compose up --build backend       # rebuild one service
docker compose down                     # stop everything
docker compose down -v                  # full reset including volumes
docker compose exec backend bash        # shell inside backend container
```

---

## Retraining the Vector Store

```bash
# 1. Wipe the existing store
docker compose down -v
# or locally:
rm -rf backend/app/chroma_store

# 2. Add/remove files in backend/app/datasets/

# 3. Restart and reinitialise
docker compose up -d
curl -X POST http://localhost:8000/initialize
```

---

## Local Setup (macOS Intel only)

> Use Docker unless you specifically need to run without it.
> Apple Silicon users: use Docker or `pip install torch` directly — no source build needed.

### Why PyTorch must be built from source
There are no prebuilt PyTorch wheels for macOS Intel (x86_64) for versions >= 2.4.0.
This is not an issue inside Docker (Linux containers have prebuilt wheels for all architectures).

### Important: No spaces in the project path
The NNPACK/peachpy build step breaks on paths containing spaces. Ensure your
project lives at a space-free path e.g. `~/Developer/oceansense-ai` not
`~/Documents/AI Chatbot Project/oceansense-ai`.

### Important: Keep project out of iCloud Drive
iCloud offloads files and intercepts directory creation, breaking both the
PyTorch build and Docker volume mounts. Keep the project under `~/Developer/`.

### Step 1 — Clone and set up virtual environment
```bash
git clone https://github.com/dennisarimi/oceansense-ai.git
cd oceansense-ai/backend

python3.12 -m venv venv
source venv/bin/activate
```

### Step 2 — Install a CMake 3.x into the venv
CMake 4.x (current Homebrew default) is incompatible with PyTorch v2.4.1 submodules.
Install a pinned version directly into the venv so it takes precedence:

```bash
pip install "cmake>=3.18,<4.0"
cmake --version   # must print 3.x.x
```

### Step 3 — Install backend dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Clone and prepare PyTorch source
```bash
git clone https://github.com/pytorch/pytorch.git
cd pytorch
git checkout v2.4.1
git submodule sync
git submodule update --init --recursive
```

### Step 5 — Install PyTorch build dependencies
```bash
pip install -r requirements.txt
```

### Step 6 — Build PyTorch from source
Takes 30–90 minutes. Set `MAX_JOBS` to your CPU core count.

```bash
export CXXFLAGS="-Wno-deprecated-declarations"

USE_CUDA=0 \
USE_XPU=0 \
USE_FBGEMM=0 \
USE_NNPACK=0 \
USE_QNNPACK=0 \
USE_PYTORCH_QNNPACK=0 \
USE_DISTRIBUTED=0 \
BUILD_TEST=0 \
MAX_JOBS=8 \
python -m pip install --no-build-isolation -v -e .
```

| Flag | Reason |
|------|--------|
| `USE_CUDA=0` / `USE_XPU=0` | CPU-only build; no GPU on Intel Mac |
| `USE_FBGEMM=0` | fbgemm uses VLAs that AppleClang 17 rejects as errors |
| `USE_NNPACK=0` / `USE_QNNPACK=0` / `USE_PYTORCH_QNNPACK=0` | peachpy assembly tool breaks on paths with spaces |
| `USE_DISTRIBUTED=0` | Not needed for single-machine inference |
| `BUILD_TEST=0` | Skips test binaries, saves significant build time |

Success looks like:
```
Successfully installed torch-2.4.0a0+giteeXXXXXX
```

### Step 7 — Spoof the PyTorch version string
The pre-release version string causes `sentence-transformers` and `transformers`
to reject the build. Add this to your shell profile to make it permanent:

```bash
echo 'export TORCH_VERSION_OVERRIDE="2.4.0"' >> ~/.zshrc
source ~/.zshrc
```

### Step 8 — Verify PyTorch
```bash
python -c "import torch; print(torch.__version__); print(torch.tensor([1.0, 2.0]))"
# Expected: prints version string and tensor([1., 2.])
```

### Running locally
```bash
source venv/bin/activate
export TORCH_VERSION_OVERRIDE="2.4.0"   # skip if added to shell profile
uvicorn app.main:app --reload --reload-dir=app
```

Server available at http://127.0.0.1:8000. Ready when you see:
```
INFO:     Application startup complete.
```

---

## User Testing with Ngrok

For sharing the app with external testers without deploying to a server.

### Setup (one time)
```bash
brew install ngrok
ngrok config add-authtoken YOUR_TOKEN   # from ngrok.com dashboard
```

Add an alias for convenience:
```bash
echo 'alias ngrok-start="ngrok start --all --config ~/Library/Application\ Support/ngrok/ngrok.yml"' >> ~/.zshrc
source ~/.zshrc
```

### ngrok.yml config
Located at `~/Library/Application Support/ngrok/ngrok.yml`:
```yaml
version: "3"
agent:
  authtoken: YOUR_TOKEN_HERE

tunnels:
  frontend:
    addr: 3000
    proto: http
  backend:
    addr: 8000
    proto: http
```

> **Free tier limitation:** Both tunnels share the same domain. To have separate
> URLs for frontend and backend (needed for external testers), upgrade to the
> paid plan ($10/mo) or use the workaround below.

### Free tier workaround for external testing
Run the frontend outside Docker and tunnel only the backend:

```bash
# Terminal 1 — backend via Docker
docker compose up -d

# Terminal 2 — tunnel backend only
ngrok http 8000

# Terminal 3 — frontend pointed at backend tunnel
NEXT_PUBLIC_API_URL=https://YOUR-TUNNEL.ngrok-free.app npm run dev
```

Share the frontend ngrok URL with testers.

### Per-session workflow (paid tier)
```bash
# 1. Start app with backend tunnel URL baked into frontend
NEXT_PUBLIC_API_URL=https://YOUR-BACKEND-TUNNEL.ngrok-free.app \
  docker compose up -d --build

# 2. Start tunnels
ngrok-start

# 3. Share frontend tunnel URL with testers
```

> Ngrok URLs change every session on the free tier. Coordinate timing with
> testers or upgrade for static domains.

---

## Key Dependencies and Pinned Versions

| Package | Version | Reason pinned |
|---------|---------|---------------|
| `torch` | 2.4.1 | No macOS Intel wheels above this; built from source locally |
| `transformers` | 4.44.2 | Newer versions have a `NameError: nn not defined` bug on import |
| `sentence-transformers` | 3.0.1 | Import-time breakage with newer transformers on macOS |
| `cmake` | >=3.18,<4.0 | CMake 4.x breaks PyTorch v2.4.1 third-party submodules |

---

## Troubleshooting

**`zsh: command not found: uvicorn`**
Venv not activated. Run `source venv/bin/activate`.

**`CMake Error: Compatibility with CMake < 3.5 has been removed`**
CMake 4.x is active. Run `pip install "cmake>=3.18,<4.0"` inside the venv.

**`NameError: name 'nn' is not defined`** (in transformers)
Wrong transformers version. Run `pip install "transformers==4.44.2"`.

**`ModuleNotFoundError: No module named 'typing_extensions'`**
Run `pip install typing_extensions` inside the venv.

**Build fails with VLA errors in fbgemm**
Add `USE_FBGEMM=0` to the build command.

**`No such file or directory` errors with spaces in path**
Move the project to a path without spaces e.g. `~/Developer/oceansense-ai`.

**`operation not permitted` Docker mount errors**
Project is inside iCloud Drive. Move to `~/Developer/oceansense-ai`.

**`Disabling PyTorch because PyTorch >= 2.4 is required but found 2.4.0a0+...`**
Run `export TORCH_VERSION_OVERRIDE="2.4.0"` before starting the server.

**`curl: (28) Failed to connect to localhost port 8000`**
Server crashed on startup. Check terminal for Python traceback above the curl timeout.

**Ollama container unhealthy**
Ollama takes time to load. The health check uses `ollama list` which is the
most reliable readiness probe. If it still fails, run `docker compose down`
and `docker compose up` again — the model is cached in the `ollama_models` volume.

**ngrok tunnel works but app requests don't go through it**
Expected when running locally — the frontend hits `localhost:8000` directly.
The tunnel is only needed for external testers. Rebuild the frontend with
`NEXT_PUBLIC_API_URL=https://your-tunnel.ngrok-free.app docker compose up --build frontend`.

---

## Code Ocean Reproducibility

A `run` script is included in the repo root for Code Ocean submission.
It builds the full stack via Docker Compose, waits for all services to become
healthy, runs an end-to-end test query, and saves artifacts to `/results/`.

```bash
./run
```

Requires Docker to be installed and running on the reviewer's machine.
