# ── Hugging Face Spaces — CineVault API ──────────────────────────────────────
# HF Spaces requires port 7860 for Docker apps.
# The ML artifacts (recommendations.json, clean_data.json, etc.) are included
# in the repo under ml/artifacts/ so the API serves from pre-built cache.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Pillow / colorthief
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole project
COPY . .

# Expose port 7860 (required by HF Spaces)
EXPOSE 7860

# Start the FastAPI server on port 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
