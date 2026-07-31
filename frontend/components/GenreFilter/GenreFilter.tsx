"use client";

import { useRef } from "react";
import { motion } from "framer-motion";

interface GenreFilterProps {
  genres: string[];
  activeGenre: string | null;
  onGenreSelect: (genre: string | null) => void;
}

export function GenreFilter({ genres, activeGenre, onGenreSelect }: GenreFilterProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  if (!genres.length) return null;

  return (
    <div className="relative w-full mb-8" ref={containerRef}>
      <div className="flex gap-2 overflow-x-auto no-scrollbar px-4 md:px-12 py-2 snap-x">
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={() => onGenreSelect(null)}
          className={`snap-start shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-colors border ${
            activeGenre === null
              ? "bg-white text-black border-white"
              : "bg-bg-elevated text-white border-white/10 hover:border-white/30"
          }`}
        >
          All Genres
        </motion.button>

        {genres.map((genre) => (
          <motion.button
            key={genre}
            whileTap={{ scale: 0.95 }}
            onClick={() => onGenreSelect(genre)}
            className={`snap-start shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-colors border ${
              activeGenre === genre
                ? "bg-white text-black border-white"
                : "bg-bg-elevated text-white border-white/10 hover:border-white/30"
            }`}
          >
            {genre}
          </motion.button>
        ))}
      </div>
    </div>
  );
}
