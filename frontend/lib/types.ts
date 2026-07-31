export type MetadataCompleteness = "full" | "partial" | "minimal";
export type RecommendationBasis = "content_similarity" | "genre_match" | "popularity_fallback";
export type SimilarityTier = "Excellent Match" | "Great Match" | "Good Match" | "Decent Match" | "Related";

export interface TitleSummary {
  show_id: string;
  type: string;
  title: string;
  primary_genre: string;
  genres_list: string[];
  release_year: number | null;
  rating: string | null;
  duration: string | null;
  poster_url: string | null;
  metadata_completeness: MetadataCompleteness;
  accent_color: string | null;  // hex color extracted from backdrop, null = use global gold
}

export interface TitleDetail {
  show_id: string;
  type: string;
  title: string;
  director: string;
  country: string | null;
  country_list: string[];
  primary_country: string | null;
  date_added: string | null;
  release_year: number | null;
  rating: string | null;
  rating_tier: string | null;
  duration: string | null;
  duration_value: number | null;
  duration_unit: string | null;
  listed_in: string | null;
  genres_list: string[];
  primary_genre: string;
  metadata_completeness: MetadataCompleteness;
  poster_url: string | null;
  backdrop_url: string | null;
  tmdb_overview: string | null;
  tmdb_id: number | null;
  accent_color: string | null;
}

export interface RecommendationItem {
  show_id: string;
  rank: number;
  score: number;
  recommendation_basis: RecommendationBasis;
  similarity_tier: SimilarityTier;
  title: TitleSummary;
}

export interface RecommendationsResponse {
  query_id: string;
  query_title: string;
  count: number;
  recommendation_basis: RecommendationBasis;
  recommendations: RecommendationItem[];
}

export interface TitlesListResponse {
  total: number;
  page: number;
  per_page: number;
  pages: number;
  titles: TitleSummary[];
}

export interface SearchResult {
  show_id: string;
  title: string;
  type: string;
  release_year: number | null;
  primary_genre: string;
  poster_url: string | null;
  match_score: number;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchResult[];
}

export interface GenresResponse {
  genres: string[];
}

// ── AI Search Types ───────────────────────────────────────────────────────────

export interface AISearchIntent {
  genres: string[];
  mood: string[];
  similar_to: string[];
  avoid: string[];
  raw_query: string;
}

export interface AISearchResponse {
  query: string;
  intent: AISearchIntent | null;
  results: SearchResult[];
  count: number;
  fallback: boolean;
  fallback_reason: string | null;
}
