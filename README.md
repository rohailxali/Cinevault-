# CineVault

A premium, Netflix-style content discovery web app powered by content-based ML recommendations.

## Overview

CineVault is built on a real-world dataset of ~8,800 titles (movies and TV shows). Unlike typical ML demos, this project handles the messy realities of the dataset (missing descriptions, missing cast, missing posters) and degrades gracefully with honest UI copy and deterministic UI fallbacks.

The system is broken into three decoupled tiers:
1. **Offline ML Pipeline (Python)**: Cleans data, fetches TMDB enrichment (async), builds TF-IDF profiles, precomputes similarities, and applies MMR (Maximal Marginal Relevance) re-ranking. Outputs static JSON/NPZ artifacts.
2. **Serving API (FastAPI)**: Loads the ML artifacts into memory at startup. Serves recommendations in O(1) time without any on-the-fly matrix math.
3. **Frontend (Next.js 14 + Framer Motion)**: A premium, dark-themed, cinematic UI featuring layout morphing (layoutId), stagger animations, and debounced fuzzy search.

## Features

- **Content-based Filtering**: Weighted TF-IDF vectors (genres 3x, director 2x) with cosine similarity.
- **MMR Re-ranking**: Prevents recommendation homogenization (e.g., stopping 10 franchise sequels from dominating the top spots).
- **Graceful Degradation**: 
  - Titles lacking strong metadata fall back from "Content Similarity" to "Genre Match" or "Popularity Fallback".
  - Titles without a TMDB poster generate a unique, deterministic HSL gradient based on their title hash.
- **Cinematic UX**: Shared element transitions morph title cards into full-screen modals just like native TV apps.

## Setup & Running

### Prerequisites
- Python 3.10+
- Node.js 18+

### 🛠 Tech Stack

- **Frontend:** Next.js 14, React 18, TailwindCSS, Framer Motion, TypeScript
- **Backend:** FastAPI, Python 3.12, Uvicorn, ColorThief, Anthropic Claude
- **Data Engine:** Pandas, RapidFuzz, Scikit-learn (TF-IDF/Cosine Similarity)

---

## 🚀 Getting Started

### 1. Backend (FastAPI + AI/ML Engine)

Navigate to the root directory and create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install anthropic colorthief

# Create an .env file and add your Claude API key for AI search:
echo "ANTHROPIC_API_KEY=sk-ant-xxx" > .env

# Run the backend
python -m uvicorn api.main:app --port 8000 --reload
```
API runs on `http://localhost:8000`. Swagger docs at `/docs`.

### 3. Start the Next.js Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on `http://localhost:3000`.

## Architecture & Scalability Path

Currently, the similarities are precomputed into a dense cache for 8,800 titles. This fits easily in memory (~25MB). 

**To scale to 100k+ titles:**
1. **Vector Storage**: Swap `linear_kernel` for **FAISS** (`IndexFlatIP` for exact dot-product or `IndexIVFFlat` for approximate nearest neighbors).
2. **Serving**: Move the `recommendations.json` cache into **Redis** (serialized with MsgPack) rather than loading it all into the FastAPI process memory.
3. **Hybrid Signal**: The API already has an `/api/events` endpoint stub. Feed these click events into a matrix factorization model (e.g., implicit ALS) and blend the collaborative filtering scores with our existing content-based scores in `ranking.py`.
