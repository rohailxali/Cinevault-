"use client";

import { useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { TitleSummary } from "@/lib/types";
import { TitleCard } from "../TitleCard/TitleCard";
import { RowSkeleton } from "../ui/Skeleton";

interface CategoryRowProps {
  title: string;
  titles: TitleSummary[];
  onTitleClick: (id: string) => void;
  isLoading?: boolean;
}

export function CategoryRow({ title, titles, onTitleClick, isLoading = false }: CategoryRowProps) {
  const rowRef = useRef<HTMLDivElement>(null);
  const prefersReduced = useReducedMotion();

  const scroll = (direction: "left" | "right") => {
    if (rowRef.current) {
      const { scrollLeft, clientWidth } = rowRef.current;
      const scrollTo = direction === "left" ? scrollLeft - clientWidth * 0.75 : scrollLeft + clientWidth * 0.75;
      rowRef.current.scrollTo({ left: scrollTo, behavior: "smooth" });
    }
  };

  if (isLoading) {
    return (
      <div className="mb-8 lg:mb-12">
        <h2 className="text-xl sm:text-2xl font-bold text-text-primary mb-4 px-4 md:px-12">{title}</h2>
        <RowSkeleton />
      </div>
    );
  }

  if (titles.length === 0) return null;

  return (
    <div className="relative mb-8 lg:mb-12 group">
      {/* Row header */}
      <motion.h2
        className="text-xl sm:text-2xl font-bold text-text-primary mb-4 px-4 md:px-12 flex items-center gap-2 cursor-default"
        initial={prefersReduced ? false : { opacity: 0, x: -10 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.4 }}
      >
        {title}
        <ChevronRight className="w-5 h-5 text-text-secondary opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
      </motion.h2>

      {/* Left scroll button */}
      <button
        onClick={() => scroll("left")}
        className="absolute left-0 top-[56px] bottom-0 w-12 z-20 items-center justify-center bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity hidden md:flex hover:bg-black/80"
        aria-label="Scroll left"
      >
        <ChevronLeft className="w-7 h-7 text-white" />
      </button>

      {/* Cards track */}
      <div
        ref={rowRef}
        className="flex gap-3 sm:gap-4 overflow-x-auto no-scrollbar px-4 md:px-12 pb-4 pt-1 snap-x snap-mandatory"
        style={{ scrollBehavior: "smooth" }}
      >
        {titles.map((t, index) => (
          <motion.div
            key={t.show_id}
            className="snap-start shrink-0"
            initial={prefersReduced ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{
              duration: 0.35,
              delay: prefersReduced ? 0 : Math.min(index * 0.04, 0.3), // cap stagger at 300ms
              ease: "easeOut",
            }}
          >
            <TitleCard title={t} onClick={onTitleClick} />
          </motion.div>
        ))}
      </div>

      {/* Right scroll button */}
      <button
        onClick={() => scroll("right")}
        className="absolute right-0 top-[56px] bottom-0 w-12 z-20 items-center justify-center bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity hidden md:flex hover:bg-black/80"
        aria-label="Scroll right"
      >
        <ChevronRight className="w-7 h-7 text-white" />
      </button>
    </div>
  );
}
