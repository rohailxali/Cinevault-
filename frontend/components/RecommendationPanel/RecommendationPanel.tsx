"use client";

import { motion } from "framer-motion";
import { RecommendationItem, RecommendationBasis, SimilarityTier } from "@/lib/types";
import { TitleCard } from "../TitleCard/TitleCard";

interface RecommendationPanelProps {
  recommendations: RecommendationItem[];
  basisLabel: string;
  onTitleClick: (id: string) => void;
}

// ── Visual tier system ───────────────────────────────────────────────────────
const TIER_CONFIG: Record<SimilarityTier, { bars: number; color: string; label: string }> = {
  "Excellent Match": { bars: 4, color: "#4ade80", label: "Excellent" },
  "Great Match":     { bars: 3, color: "#86efac", label: "Great" },
  "Good Match":      { bars: 2, color: "#C9A24B", label: "Good" },
  "Decent Match":    { bars: 1, color: "#8a8a9a", label: "Decent" },
  "Related":         { bars: 1, color: "#555568", label: "Related" },
};

const BASIS_CHIP: Record<RecommendationBasis, { icon: string; text: string }> = {
  "content_similarity": { icon: "◈", text: "Content match" },
  "genre_match":        { icon: "◉", text: "Genre match" },
  "popularity_fallback":{ icon: "↑", text: "Trending" },
};

function MatchBar({ tier }: { tier: SimilarityTier }) {
  const config = TIER_CONFIG[tier] || TIER_CONFIG["Related"];
  return (
    <div className="flex items-center gap-1 mt-2">
      <div className="flex gap-0.5">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="w-5 h-1 rounded-full transition-colors"
            style={{
              backgroundColor: i <= config.bars ? config.color : "#2a2a38",
            }}
          />
        ))}
      </div>
      <span className="text-[9px] font-semibold tracking-wider uppercase ml-1" style={{ color: config.color }}>
        {config.label}
      </span>
    </div>
  );
}

function BasisChip({ basis }: { basis: RecommendationBasis }) {
  const chip = BASIS_CHIP[basis] || { icon: "·", text: "Recommended" };
  return (
    <div className="flex items-center gap-1 mt-1">
      <span className="text-[10px] text-text-secondary">
        <span className="text-brand mr-0.5">{chip.icon}</span>
        {chip.text}
      </span>
    </div>
  );
}

export function RecommendationPanel({
  recommendations,
  basisLabel,
  onTitleClick,
}: RecommendationPanelProps) {
  if (!recommendations.length) return null;

  return (
    <div className="mt-8 pt-8 border-t border-white/10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-text-primary font-display">More Like This</h3>
        <span className="text-xs text-text-secondary italic">{basisLabel}</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {recommendations.map((item, index) => (
          <motion.div
            key={item.show_id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04, duration: 0.35, ease: "easeOut" }}
            className="flex flex-col"
          >
            <TitleCard title={item.title} onClick={onTitleClick} />
            <div className="mt-2 px-0.5">
              <MatchBar tier={item.similarity_tier} />
              <BasisChip basis={item.recommendation_basis} />
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
