"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion";
import { Info, Play } from "lucide-react";
import { TitleSummary } from "@/lib/types";

const BRAND_GOLD = "#C9A24B";

interface HeroSectionProps {
  title: TitleSummary | null;
  onMoreInfo: (id: string) => void;
}

export function HeroSection({ title, onMoreInfo }: HeroSectionProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const prefersReduced = useReducedMotion();

  // Scroll-driven parallax values — scoped to hero container
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end start"],
  });

  const bgY = useTransform(scrollYProgress, [0, 1], prefersReduced ? ["0%", "0%"] : ["0%", "25%"]);
  const contentOpacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);
  const contentY = useTransform(scrollYProgress, [0, 0.6], prefersReduced ? ["0px", "0px"] : ["0px", "30px"]);

  if (!title) {
    return <div ref={containerRef} className="w-full h-[60vh] md:h-[85vh] bg-bg-base animate-pulse" />;
  }

  const bgImage = (title as any).backdrop_url || title.poster_url;
  const accent = title.accent_color || BRAND_GOLD;

  return (
    <div ref={containerRef} className="relative w-full h-[60vh] md:h-[85vh] bg-bg-base overflow-hidden">
      {/* Parallax background image */}
      <motion.div
        className="absolute inset-0 will-change-transform"
        style={{ y: bgY }}
      >
        <motion.div
          initial={{ scale: 1.06 }}
          animate={{ scale: 1 }}
          transition={{ duration: prefersReduced ? 0 : 12, ease: "easeOut" }}
          className="w-full h-full"
        >
          {bgImage ? (
            <img
              src={bgImage}
              alt={title.title}
              className="w-full h-full object-cover object-top"
              style={{ opacity: 0.55 }}
            />
          ) : (
            <div className="w-full h-full" style={{ background: `linear-gradient(135deg, ${accent}33, #0a0a0f)` }} />
          )}
        </motion.div>
      </motion.div>

      {/* Dynamic color gradient overlay — tinted by per-title accent */}
      <motion.div
        className="absolute inset-0"
        animate={{ opacity: 1 }}
        style={{
          background: `linear-gradient(to top, #0a0a0f 0%, #0a0a0f44 40%, transparent 70%),
                       linear-gradient(to right, #0a0a0f 0%, #0a0a0f66 50%, transparent 80%)`,
        }}
      />

      {/* Subtle accent glow at bottom — changes per title */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 h-48 pointer-events-none"
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4 }}
        style={{
          background: `radial-gradient(ellipse 60% 100% at 20% 100%, ${accent}22, transparent)`,
        }}
      />

      {/* Foreground content — fades and slides as you scroll */}
      <motion.div
        className="absolute inset-0 flex flex-col justify-end px-4 md:px-12 pb-32 md:pb-48 z-10"
        style={{ opacity: contentOpacity, y: contentY }}
      >
        <motion.div
          key={title.show_id}
          initial={{ opacity: 0, y: prefersReduced ? 0 : 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: prefersReduced ? 0 : 0.7, ease: "easeOut" }}
          className="max-w-2xl"
        >
          {/* Meta row */}
          <div className="flex items-center gap-3 mb-4 text-xs font-semibold text-text-secondary drop-shadow-md">
            <span className="tracking-widest uppercase" style={{ color: accent }}>CineVault Original</span>
            {title.release_year && <span>• {title.release_year}</span>}
            {title.rating && (
              <span className="px-1.5 py-0.5 border border-text-secondary/50 rounded text-text-secondary">
                {title.rating}
              </span>
            )}
            {title.duration && <span>• {title.duration}</span>}
          </div>

          {/* Display serif title */}
          <h1 className="font-display text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-4 leading-tight text-shadow-lg">
            {title.title}
          </h1>

          {/* Genre row */}
          <div className="flex items-center gap-3 text-text-primary text-sm font-medium mb-8">
            <span className="font-semibold" style={{ color: accent }}>{title.type}</span>
            <span className="text-text-secondary">|</span>
            <span className="text-text-secondary">{title.genres_list.slice(0, 3).join(" • ")}</span>
          </div>

          {/* CTA buttons */}
          <div className="flex items-center gap-3">
            <button
              className="flex items-center gap-2 bg-white text-black px-7 py-2.5 rounded-md font-bold hover:bg-white/90 transition-colors focus-visible:outline-2 focus-visible:outline-white"
            >
              <Play className="w-5 h-5 fill-current" />
              <span>Play</span>
            </button>
            <button
              onClick={() => onMoreInfo(title.show_id)}
              className="flex items-center gap-2 px-7 py-2.5 rounded-md font-bold transition-all backdrop-blur-sm border focus-visible:outline-2 hover:opacity-90"
              style={{
                borderColor: `${accent}60`,
                background: `${accent}18`,
                color: accent,
              }}
            >
              <Info className="w-5 h-5" />
              <span>More Info</span>
            </button>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
