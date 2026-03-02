# OceanSense AI — Backend Setup

## System Requirements

- macOS 15+ (Intel x86_64) — these instructions are written for Intel Mac
- Python 3.12
- Xcode Command Line Tools (`xcode-select --install`)
- Homebrew

---

## ⚠️ Important: PyTorch Must Be Built From Source on macOS Intel

There are no prebuilt PyTorch wheels for macOS Intel (`x86_64`) for versions >= 2.4.0.
You must build PyTorch from source before installing the rest of the dependencies.
Follow **all steps below in order**.

---

## Step 1 — Clone the repo and set up the virtual environment

```bash
git clone <your-repo-url> oceansense-ai
cd oceansense-ai/backend

python3.12 -m venv venv
source venv/bin/activate
```

> Always activate the venv before running any commands in this project.
> You should see `(venv)` in your terminal prompt.

---

## Step 2 — Install a CMake 3.x into the venv

CMake 4.x (the current Homebrew default) is **incompatible** with PyTorch v2.4.1's
third-party submodules. Install a pinned CMake 3.x directly into your venv so it
takes precedence over the system CMake:

```bash
pip install "cmake>=3.18,<4.0"
cmake --version   # should print 3.x.x
```

---

## Step 3 — Clone and prepare the PyTorch source

```bash
# From the backend/ directory
git clone --branch v2.4.1 --depth 1 https://github.com/pytorch/pytorch.git
cd pytorch

git submodule sync
git submodule update --init --recursive
```

---

## Step 4 — Install PyTorch build dependencies

```bash
pip install typing_extensions pyyaml numpy setuptools
pip install -r requirements.txt
```

---

## Step 5 — Build PyTorch from source

This step takes 30–90 minutes depending on your machine. `MAX_JOBS` controls
parallel compilation — set it to the number of CPU cores you want to use.

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

**Why these flags?**

| Flag | Reason |
|------|--------|
| `USE_CUDA=0` / `USE_XPU=0` | CPU-only build; no GPU on Intel Mac |
| `USE_FBGEMM=0` | fbgemm uses VLAs that AppleClang 17 rejects as errors |
| `USE_NNPACK=0` / `USE_QNNPACK=0` / `USE_PYTORCH_QNNPACK=0` | These submodules use `python-peachpy` which breaks on paths with spaces and isn't needed for inference |
| `USE_DISTRIBUTED=0` | Not needed for single-machine inference |
| `BUILD_TEST=0` | Skips building test binaries, saving significant build time |

After a successful build you should see:
```
Successfully installed torch-2.4.0a0+giteeXXXXXX
```

---

## Step 6 — Spoof the PyTorch version string

The build produces a pre-release version string (`2.4.0a0+...`) which causes
`sentence-transformers` and `transformers` to reject it even though it is fully
functional. Export this variable before starting the server, or add it to your
shell profile / `.env` file:

```bash
export TORCH_VERSION_OVERRIDE="2.4.0"
```

To make this permanent, add it to your shell profile:
```bash
echo 'export TORCH_VERSION_OVERRIDE="2.4.0"' >> ~/.zshrc
source ~/.zshrc
```

---

## Step 7 — Install remaining backend dependencies

```bash
# From the backend/ directory (not pytorch/)
cd ..
pip install -r requirements.txt
```

---

## Step 8 — Verify PyTorch is working

```bash
python -c "import torch; print(torch.__version__); print(torch.tensor([1.0, 2.0]))"
```

Expected output:
```
2.4.0a0+giteeXXXXXX
tensor([1., 2.])
```

---

## Running the Application

Always run from the `backend/` directory with the venv activated:

```bash
source venv/bin/activate
export TORCH_VERSION_OVERRIDE="2.4.0"   # skip if added to shell profile
uvicorn app.main:app --reload --reload-dir=app
```

The server will be available at `http://127.0.0.1:8000`.

---

## Retraining / Reinitialising the Vector Store

1. Delete the `chroma_store/` folder:
   ```bash
   rm -rf app/chroma_store
   ```
2. Add or remove dataset files in `app/datasets/`
3. With the server running, trigger reinitialization:
   ```bash
   curl -X POST http://localhost:8000/initialize
   ```

---

## Troubleshooting

**`zsh: command not found: uvicorn`**
Your venv is not activated. Run `source venv/bin/activate` first.

**`Disabling PyTorch because PyTorch >= 2.4 is required but found 2.4.0a0+...`**
The version spoof is not set. Export `TORCH_VERSION_OVERRIDE="2.4.0"` before starting the server.

**`CMake Error: Compatibility with CMake < 3.5 has been removed`**
CMake 4.x is being used. Make sure you ran `pip install "cmake>=3.18,<4.0"` inside the venv and that `cmake --version` prints 3.x while the venv is active.

**`NameError: name 'nn' is not defined`** (in transformers)
You have a newer version of `transformers` installed. Pin it: `pip install "transformers==4.44.2"`.

**`ModuleNotFoundError: No module named 'typing_extensions'`**
Run `pip install typing_extensions` inside the venv.

**Build fails with VLA errors in fbgemm**
Make sure `USE_FBGEMM=0` is set in your build command. AppleClang 17 rejects variable-length arrays in C++.

**`curl: (28) Failed to connect to localhost port 8000`**
The server crashed on startup. Check the terminal output for a Python traceback — the actual error will be a few lines above the curl timeout.

---

## Notes for Non-macOS / Future Environments

- **Linux + CUDA**: Remove the `USE_CUDA=0` flag and uncomment the Nvidia packages in `requirements.txt`. You can likely install a prebuilt `torch` wheel via pip instead of building from source.
- **Apple Silicon (M1/M2/M3)**: Prebuilt wheels exist for `torch>=2.0` on arm64. Skip the source build entirely and use `pip install torch`.
- **Do not move or delete the `pytorch/` source directory** — the editable install (`-e .`) resolves `import torch` directly from that folder. If you move it, re-run Step 5 from the new location.