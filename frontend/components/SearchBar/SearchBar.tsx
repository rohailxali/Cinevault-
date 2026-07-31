"use client";

import { useState, useEffect, useRef } from "react";
import { Search, X, Sparkles, Loader2 } from "lucide-react";
import { useDebounceValue } from "usehooks-ts";
import { motion, AnimatePresence } from "framer-motion";
import { SearchResult, AISearchResponse } from "@/lib/types";
import { searchTitles, aiSearch } from "@/lib/api";

interface SearchBarProps {
  onTitleClick: (id: string) => void;
  onOpenPalette?: () => void;
}

export function SearchBar({ onTitleClick, onOpenPalette }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [debouncedQuery] = useDebounceValue(query, 350);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isAIMode, setIsAIMode] = useState(false);
  const [isFallback, setIsFallback] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Search effect — handles both keyword and AI modes
  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([]);
      setIsSearching(false);
      setIsFallback(false);
      return;
    }

    let isMounted = true;
    setIsSearching(true);

    const doSearch = isAIMode
      ? aiSearch(debouncedQuery).then((res: AISearchResponse) => {
          if (isMounted) {
            setResults(res.results);
            setIsFallback(res.fallback);
          }
        })
      : searchTitles(debouncedQuery).then((res) => {
          if (isMounted) {
            setResults(res.results);
            setIsFallback(false);
          }
        });

    doSearch
      .catch((err) => console.error("Search failed", err))
      .finally(() => { if (isMounted) setIsSearching(false); });

    return () => { isMounted = false; };
  }, [debouncedQuery, isAIMode]);

  const handleResultClick = (id: string) => {
    setIsOpen(false);
    setQuery("");
    onTitleClick(id);
  };

  const toggleAIMode = () => {
    setIsAIMode((prev) => !prev);
    setResults([]);
    setIsFallback(false);
  };

  return (
    <div ref={wrapperRef} className="relative w-full max-w-sm">
      {/* Search input */}
      <div
        className={`flex items-center border transition-all duration-200 rounded-full px-3 py-2 gap-2 ${
          isOpen
            ? isAIMode
              ? "border-brand/60 bg-bg-elevated shadow-[0_0_12px_var(--color-brand-glow)]"
              : "border-brand/40 bg-bg-elevated"
            : "border-white/10 bg-bg-surface hover:border-white/25"
        }`}
      >
        <Search className="w-4 h-4 text-text-secondary shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setIsOpen(true); }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && results.length > 0) {
              handleResultClick(results[0].show_id);
            }
          }}
          placeholder={isAIMode ? "Ask Cinevault anything…" : "Search movies, TV shows..."}
          className="bg-transparent border-none outline-none text-text-primary w-full text-sm placeholder:text-text-secondary"
        />

        {/* Loading spinner */}
        {isSearching && <Loader2 className="w-4 h-4 text-brand animate-spin shrink-0" />}

        {/* Clear button */}
        {query && !isSearching && (
          <button onClick={() => { setQuery(""); setResults([]); }} className="p-0.5 hover:bg-white/10 rounded-full shrink-0">
            <X className="w-3.5 h-3.5 text-text-secondary" />
          </button>
        )}

        {/* AI mode toggle */}
        <button
          onClick={toggleAIMode}
          title={isAIMode ? "Switch to keyword search" : "Ask Cinevault with AI"}
          className={`shrink-0 p-1 rounded-full transition-all ${
            isAIMode ? "text-brand bg-brand/10" : "text-text-secondary hover:text-brand hover:bg-brand/5"
          }`}
        >
          <Sparkles className="w-4 h-4" />
        </button>
      </div>

      {/* AI mode label */}
      <AnimatePresence>
        {isAIMode && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute -bottom-5 left-3 text-[10px] text-brand/70 font-medium tracking-wide"
          >
            ✦ AI MODE
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results dropdown */}
      <AnimatePresence>
        {isOpen && query.trim().length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full mt-3 w-full min-w-[320px] bg-bg-surface border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50 max-h-[60vh] overflow-y-auto"
          >
            {/* Fallback notice */}
            {isFallback && !isSearching && (
              <div className="px-4 pt-3 pb-1">
                <p className="text-[10px] text-text-secondary italic">Showing closest keyword matches</p>
              </div>
            )}

            {/* AI thinking shimmer */}
            {isSearching && isAIMode ? (
              <div className="p-4 space-y-3">
                <div className="flex items-center gap-2 text-brand/70 text-xs mb-2">
                  <Sparkles className="w-3 h-3 animate-pulse" />
                  <span>Thinking…</span>
                </div>
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex gap-3 animate-pulse">
                    <div className="w-10 h-14 bg-bg-elevated rounded-md" />
                    <div className="flex-1 space-y-2 py-1">
                      <div className="h-3 bg-bg-elevated rounded w-3/4" style={{ animationDelay: `${i * 100}ms` }} />
                      <div className="h-2.5 bg-bg-elevated rounded w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
            ) : isSearching ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex gap-3 animate-pulse">
                    <div className="w-10 h-14 bg-bg-elevated rounded-md" />
                    <div className="flex-1 space-y-2 py-1">
                      <div className="h-3 bg-bg-elevated rounded w-3/4" />
                      <div className="h-2.5 bg-bg-elevated rounded w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
            ) : results.length > 0 ? (
              <div className="py-1">
                {results.map((result) => (
                  <button
                    key={result.show_id}
                    onClick={() => handleResultClick(result.show_id)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-white/5 transition-colors text-left group"
                  >
                    {result.poster_url ? (
                      <img src={result.poster_url} alt={result.title} className="w-10 h-14 object-cover rounded-md flex-shrink-0" />
                    ) : (
                      <div className="w-10 h-14 bg-gradient-to-br from-brand/20 to-bg-elevated rounded-md flex items-center justify-center text-[8px] text-text-secondary text-center p-1 font-bold flex-shrink-0">
                        {result.title.slice(0, 2)}
                      </div>
                    )}
                    <div className="flex-1 overflow-hidden">
                      <p className="text-text-primary text-sm font-medium truncate group-hover:text-brand transition-colors">{result.title}</p>
                      <p className="text-text-secondary text-xs truncate mt-0.5">
                        {result.release_year && `${result.release_year} · `}{result.type} · {result.primary_genre}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-text-secondary text-sm">
                <p>No results for &ldquo;{query}&rdquo;</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
