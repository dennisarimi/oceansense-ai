# ---------- base image (Python 3.11 full) ----------
    FROM python:3.11-slim

    # ---------- system deps ----------
    RUN apt-get update && \
        apt-get install -y --no-install-recommends \
            build-essential \
            git \
            && rm -rf /var/lib/apt/lists/*
    
    # ---------- set workdir ----------
    WORKDIR /app
    
    # ---------- copy requirements & install ----------
    COPY requirements.txt .
    RUN pip install --no-cache-dir --upgrade pip \
        && pip install --no-cache-dir -r requirements.txt
    
    # ---------- copy source ----------
    COPY app/ app/
    COPY datasets/ datasets/         
    
    # ---------- create writable Chroma store ----------
    RUN mkdir -p /app/chroma_store
    
    # ---------- uvicorn startup command ----------
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    