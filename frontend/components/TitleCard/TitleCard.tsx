"use client";

import { motion } from "framer-motion";
import { TitleSummary } from "@/lib/types";
import { PosterImage } from "../ui/PosterImage";

interface TitleCardProps {
  title: TitleSummary;
  onClick: (id: string) => void;
  priority?: boolean;
}

export function TitleCard({ title, onClick, priority = false }: TitleCardProps) {
  return (
    <motion.div
      layoutId={`card-container-${title.show_id}`}
      className="relative flex-none w-[140px] sm:w-[180px] md:w-[220px] aspect-[2/3] rounded-md overflow-hidden cursor-pointer group bg-bg-surface will-change-transform"
      whileHover={{ scale: 1.05, y: -5 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      onClick={() => onClick(title.show_id)}
    >
      <motion.div layoutId={`poster-container-${title.show_id}`} className="absolute inset-0">
        <PosterImage
          src={title.poster_url}
          alt={title.title}
          className="transition-opacity duration-300 group-hover:opacity-80"
          showTitleFallback={!title.poster_url}
        />
      </motion.div>

      {/* Hover Info Overlay */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3 sm:p-4"
      >
        <p className="text-white font-bold text-sm sm:text-base line-clamp-2 leading-tight mb-1">
          {title.title}
        </p>
        <div className="flex items-center gap-2 text-xs text-text-secondary font-medium">
          {title.release_year && <span>{title.release_year}</span>}
          {title.rating && (
            <span className="px-1 border border-text-secondary/50 rounded-sm text-[10px]">
              {title.rating}
            </span>
          )}
        </div>
        <p className="text-xs text-brand mt-1 font-semibold truncate">
          {title.primary_genre}
        </p>
      </motion.div>
    </motion.div>
  );
}
