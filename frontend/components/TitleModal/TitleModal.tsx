"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Play, Plus, ThumbsUp } from "lucide-react";
import { TitleDetail, RecommendationsResponse } from "@/lib/types";
import { fetchTitleDetail, fetchRecommendations } from "@/lib/api";
import { PosterImage } from "../ui/PosterImage";
import { RecommendationPanel } from "../RecommendationPanel/RecommendationPanel";
import { Skeleton } from "../ui/Skeleton";

const BRAND_GOLD = "#C9A24B";

interface TitleModalProps {
  showId: string | null;
  onClose: () => void;
  onTitleClick: (id: string) => void;
}

const formatBasis = (basis: string) => {
  switch (basis) {
    case "content_similarity":   return "Similar to this title";
    case "genre_match":          return "Matches this genre";
    case "popularity_fallback":  return "Popular right now";
    default:                     return "Recommended";
  }
};

export function TitleModal({ showId, onClose, onTitleClick }: TitleModalProps) {
  const [detail, setDetail] = useState<TitleDetail | null>(null);
  const [recs, setRecs] = useState<RecommendationsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!showId) return;
    document.body.style.overflow = "hidden";

    const loadData = async () => {
      setIsLoading(true);
      setDetail(null);
      setRecs(null);
      try {
        const [d, r] = await Promise.all([
          fetchTitleDetail(showId),
          fetchRecommendations(showId).catch(() => null),
        ]);
        setDetail(d);
        setRecs(r);
      } catch (err) {
        console.error("Failed to load title detail", err);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();

    return () => {
      document.body.style.overflow = "auto";
    };
  }, [showId]);

  if (!showId) return null;

  const accent = detail?.accent_color || BRAND_GOLD;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8 pt-12">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/85 backdrop-blur-sm cursor-pointer"
          onClick={onClose}
        />

        {/* Modal content */}
        <motion.div
          layoutId={`card-container-${showId}`}
          className="relative w-full max-w-4xl max-h-[90vh] bg-bg-surface rounded-2xl overflow-y-auto no-scrollbar shadow-2xl z-10"
          style={{ boxShadow: `0 0 60px ${accent}22` }}
        >
          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 z-50 p-2 bg-black/60 hover:bg-black/80 rounded-full text-white transition-colors backdrop-blur-md"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Hero image */}
          <div className="relative w-full aspect-video md:aspect-[21/9] bg-bg-base overflow-hidden">
            {detail?.backdrop_url || detail?.poster_url ? (
              <img
                src={detail.backdrop_url || detail.poster_url!}
                alt={detail.title || ""}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full" style={{ background: `linear-gradient(135deg, ${accent}33, #0a0a0f)` }} />
            )}

            {/* Gradient fade */}
            <div className="absolute inset-0 bg-gradient-to-t from-bg-surface via-bg-surface/30 to-transparent" />

            {/* Dynamic accent glow at bottom */}
            <div
              className="absolute bottom-0 left-0 right-0 h-32 pointer-events-none"
              style={{ background: `radial-gradient(ellipse 80% 100% at 30% 100%, ${accent}30, transparent)` }}
            />

            {/* Overlay content: title + actions */}
            <div className="absolute bottom-0 left-0 p-6 md:p-10 w-full">
              {isLoading && !detail ? (
                <Skeleton className="w-2/3 h-10 mb-4" />
              ) : (
                <>
                  <h2 className="font-display text-3xl md:text-5xl font-bold text-white mb-5 text-shadow-lg leading-tight">
                    {detail?.title}
                  </h2>
                  <div className="flex items-center gap-3">
                    <button
                      className="flex items-center gap-2 bg-white text-black px-6 py-2 rounded-md font-bold hover:bg-white/90 transition-colors"
                    >
                      <Play className="w-5 h-5 fill-current" /> Play
                    </button>
                    <button
                      className="p-2 border-2 rounded-full transition-colors hover:opacity-90"
                      style={{ borderColor: `${accent}60`, color: accent }}
                    >
                      <Plus className="w-5 h-5" />
                    </button>
                    <button
                      className="p-2 border-2 rounded-full transition-colors hover:opacity-90"
                      style={{ borderColor: `${accent}60`, color: accent }}
                    >
                      <ThumbsUp className="w-5 h-5" />
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="p-6 md:p-10">
            <div className="flex flex-col md:flex-row gap-8">
              {/* Main */}
              <div className="flex-1">
                {isLoading && !detail ? (
                  <div className="space-y-2">
                    <Skeleton className="w-full h-4" />
                    <Skeleton className="w-5/6 h-4" />
                    <Skeleton className="w-4/6 h-4" />
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap items-center gap-3 text-sm mb-4">
                      <span className="font-bold tracking-wide" style={{ color: accent }}>
                        {detail?.rating_tier || "Trending"}
                      </span>
                      <span className="text-white">{detail?.release_year}</span>
                      {detail?.rating && (
                        <span className="px-1.5 py-0.5 border border-text-secondary/40 rounded text-text-secondary text-xs">
                          {detail.rating}
                        </span>
                      )}
                      <span className="text-white">{detail?.duration}</span>
                    </div>

                    <p className="text-text-primary text-sm md:text-base leading-relaxed mb-6">
                      {detail?.tmdb_overview || (
                        <span className="italic text-text-secondary">
                          No synopsis available. Explore the details below to learn more about this title.
                        </span>
                      )}
                    </p>
                  </>
                )}
              </div>

              {/* Sidebar */}
              <div className="w-full md:w-1/3 flex flex-col gap-4 text-sm">
                {isLoading && !detail ? (
                  <div className="space-y-4">
                    <Skeleton className="w-full h-12" />
                    <Skeleton className="w-full h-12" />
                  </div>
                ) : (
                  <>
                    <div>
                      <span className="text-text-secondary">Director: </span>
                      <span className="text-text-primary">{detail?.director || "Unknown"}</span>
                    </div>
                    <div>
                      <span className="text-text-secondary">Genres: </span>
                      <span className="text-text-primary">{detail?.genres_list?.join(", ") || "Unknown"}</span>
                    </div>
                    {detail?.country && (
                      <div>
                        <span className="text-text-secondary">Country: </span>
                        <span className="text-text-primary">{detail.country}</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>

            {/* Recommendations */}
            {!isLoading && recs && (
              <RecommendationPanel
                recommendations={recs.recommendations}
                basisLabel={formatBasis(recs.recommendation_basis)}
                onTitleClick={onTitleClick}
              />
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
