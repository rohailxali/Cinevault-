import {
  AISearchResponse,
  GenresResponse,
  RecommendationsResponse,
  SearchResponse,
  TitleDetail,
  TitlesListResponse,
  TitleSummary,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export async function fetchTitles(params?: {
  page?: number;
  per_page?: number;
  genre?: string;
  type?: string;
}): Promise<TitlesListResponse> {
  const url = new URL(`${API_BASE}/titles`);
  if (params?.page) url.searchParams.append("page", params.page.toString());
  if (params?.per_page) url.searchParams.append("per_page", params.per_page.toString());
  if (params?.genre) url.searchParams.append("genre", params.genre);
  if (params?.type) url.searchParams.append("type", params.type);

  const res = await fetch(url.toString(), { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error("Failed to fetch titles");
  return res.json();
}

export async function fetchFeaturedTitles(limit = 10): Promise<TitleSummary[]> {
  const res = await fetch(`${API_BASE}/titles/featured?limit=${limit}`, {
    next: { revalidate: 3600 },
  });
  if (!res.ok) throw new Error("Failed to fetch featured titles");
  return res.json();
}

export async function fetchTitleDetail(id: string): Promise<TitleDetail> {
  const res = await fetch(`${API_BASE}/titles/${id}`, {
    next: { revalidate: 3600 },
  });
  if (!res.ok) throw new Error("Failed to fetch title detail");
  return res.json();
}

export async function fetchRecommendations(id: string): Promise<RecommendationsResponse> {
  const res = await fetch(`${API_BASE}/recommendations/${id}`, {
    next: { revalidate: 3600 },
  });
  if (!res.ok) throw new Error("Failed to fetch recommendations");
  return res.json();
}

export async function searchTitles(query: string): Promise<SearchResponse> {
  if (!query) return { query: "", count: 0, results: [] };
  const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error("Failed to search");
  return res.json();
}

export async function fetchGenres(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/genres`, { next: { revalidate: 86400 } });
  if (!res.ok) throw new Error("Failed to fetch genres");
  const data: GenresResponse = await res.json();
  return data.genres;
}

export async function aiSearch(query: string): Promise<AISearchResponse> {
  if (!query.trim()) {
    return { query: "", intent: null, results: [], count: 0, fallback: true, fallback_reason: "Empty query" };
  }
  const res = await fetch(`${API_BASE}/ai-search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error("AI search request failed");
  return res.json();
}
