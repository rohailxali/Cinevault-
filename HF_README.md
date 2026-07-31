---
title: CineVault API
emoji: 🎬
colorFrom: yellow
colorTo: orange
sdk: docker
pinned: false
---

# CineVault API 🎬

FastAPI backend for the **CineVault** AI-native movie & TV show recommendation platform.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/titles` | Paginated title list (filter by genre/type) |
| `GET` | `/api/titles/featured` | Featured/hero titles |
| `GET` | `/api/titles/{id}` | Full title detail |
| `GET` | `/api/recommendations/{id}` | Content-based recommendations |
| `GET` | `/api/search?q=` | Fuzzy keyword search |
| `POST` | `/api/ai-search` | Claude-powered natural language search |
| `GET` | `/api/genres` | All available genres |
| `GET` | `/api/health` | Health check |

## Environment Variables

| Key | Description |
|-----|-------------|
| `ANTHROPIC_API_KEY` | Required for AI search (optional — falls back to keyword search) |
| `FRONTEND_URL` | Your Vercel frontend URL (for CORS) |

Swagger docs available at `/docs`.
