"use client";

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { fetchFeaturedTitles, fetchTitles, fetchGenres, aiSearch, searchTitles } from "@/lib/api";
import { TitleSummary, SearchResult } from "@/lib/types";
import { HeroSection } from "@/components/Hero/HeroSection";
import { CategoryRow } from "@/components/Carousel/CategoryRow";
import { SearchBar } from "@/components/SearchBar/SearchBar";
import { GenreFilter } from "@/components/GenreFilter/GenreFilter";
import { TitleModal } from "@/components/TitleModal/TitleModal";
import { CommandPalette } from "@/components/CommandPalette/CommandPalette";

const MAX_RECENT = 10;

export default function Home() {
  const [featured, setFeatured] = useState<TitleSummary[]>([]);
  const [titles, setTitles] = useState<TitleSummary[]>([]);
  const [genres, setGenres] = useState<string[]>([]);
  const [activeGenre, setActiveGenre] = useState<string | null>(null);

  const [isLoadingFeatured, setIsLoadingFeatured] = useState(true);
  const [isLoadingTitles, setIsLoadingTitles] = useState(true);

  const [selectedTitleId, setSelectedTitleId] = useState<string | null>(null);

  // Track recently viewed titles for the command palette
  const [recentTitles, setRecentTitles] = useState<{ id: string; title: string; type: string }[]>([]);

  // Header scroll state
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    Promise.all([fetchFeaturedTitles(10), fetchGenres()])
      .then(([f, g]) => {
        setFeatured(f);
        setGenres(g);
      })
      .catch((err) => console.error("Failed to load initial data", err))
      .finally(() => setIsLoadingFeatured(false));
  }, []);

  useEffect(() => {
    setIsLoadingTitles(true);
    fetchTitles({ page: 1, per_page: 60, genre: activeGenre || undefined })
      .then((res) => setTitles(res.titles))
      .catch((err) => console.error("Failed to load titles", err))
      .finally(() => setIsLoadingTitles(false));
  }, [activeGenre]);

  // Track recently viewed
  const handleTitleClick = useCallback((id: string) => {
    setSelectedTitleId(id);
    // Find title in our datasets
    const allTitles = [...featured, ...titles];
    const found = allTitles.find((t) => t.show_id === id);
    if (found) {
      setRecentTitles((prev) => {
        const filtered = prev.filter((r) => r.id !== id);
        return [{ id, title: found.title, type: found.type }, ...filtered].slice(0, MAX_RECENT);
      });
    }
  }, [featured, titles]);

  // Command palette handlers
  const handleAISearch = useCallback(async (query: string) => {
    if (!query.trim()) return;
    try {
      const res = await aiSearch(query);
      // Navigate to search results — for now open the first result in modal
      if (res.results.length > 0) {
        handleTitleClick(res.results[0].show_id);
      }
    } catch (e) {
      console.error("AI search from palette failed", e);
    }
  }, [handleTitleClick]);

  const handleGenreSelect = useCallback((genre: string | null) => {
    setActiveGenre(genre);
    // Scroll to content
    setTimeout(() => {
      document.getElementById("content-rows")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  }, []);

  const handleTitleSearch = useCallback((query: string) => {
    // Focus the search bar — we pass the query via a custom event
    window.dispatchEvent(new CustomEvent("cinevault:search", { detail: { query } }));
  }, []);

  // Group titles into rows
  const rows = useMemo(() => {
    if (!titles.length) return [];

    if (activeGenre) {
      const chunks = [];
      for (let i = 0; i < titles.length; i += 20) {
        chunks.push({
          title: i === 0 ? `Trending in ${activeGenre}` : `More ${activeGenre}`,
          items: titles.slice(i, i + 20),
        });
      }
      return chunks;
    } else {
      const movies = titles.filter((t) => t.type === "Movie");
      const tvShows = titles.filter((t) => t.type === "TV Show");
      const newRows = [];
      if (movies.length > 0) newRows.push({ title: "Trending Movies", items: movies.slice(0, 20) });
      if (tvShows.length > 0) newRows.push({ title: "Binge-Worthy TV Shows", items: tvShows.slice(0, 20) });
      if (movies.length > 20) newRows.push({ title: "Critically Acclaimed", items: movies.slice(20, 40) });
      return newRows.length ? newRows : [{ title: "Trending Now", items: titles.slice(0, 20) }];
    }
  }, [titles, activeGenre]);

  return (
    <main className="min-h-screen bg-bg-base overflow-x-hidden pb-20">
      {/* Command Palette — global, mounted at root */}
      <CommandPalette
        genres={genres}
        recentTitles={recentTitles}
        onTitleSearch={handleTitleSearch}
        onAISearch={handleAISearch}
        onGenreSelect={handleGenreSelect}
        onTitleClick={handleTitleClick}
      />

      {/* Header / Nav */}
      <header
        className={`fixed top-0 w-full z-40 px-4 md:px-12 py-4 flex justify-between items-center transition-all duration-300 ${
          scrolled ? "bg-bg-base/95 backdrop-blur-md shadow-lg" : "bg-gradient-to-b from-black/70 to-transparent"
        }`}
      >
        <h1 className="text-brand font-display font-bold text-2xl md:text-3xl tracking-tight cursor-default select-none">
          CineVault
        </h1>
        <div className="flex items-center gap-3">
          {/* Cmd+K hint button — rendered inside CommandPalette */}
          <SearchBar onTitleClick={handleTitleClick} />
        </div>
      </header>

      {/* Hero */}
      <HeroSection
        title={featured.length > 0 ? featured[0] : null}
        onMoreInfo={handleTitleClick}
      />

      {/* Main Content Area */}
      <div id="content-rows" className="relative z-20 -mt-24 md:-mt-32">
        <GenreFilter
          genres={genres}
          activeGenre={activeGenre}
          onGenreSelect={handleGenreSelect}
        />

        {isLoadingTitles ? (
          <>
            <CategoryRow title="Trending Now" titles={[]} onTitleClick={() => {}} isLoading={true} />
            <CategoryRow title="Popular Picks" titles={[]} onTitleClick={() => {}} isLoading={true} />
          </>
        ) : (
          rows.map((row, idx) => (
            <CategoryRow
              key={idx}
              title={row.title}
              titles={row.items}
              onTitleClick={handleTitleClick}
            />
          ))
        )}
      </div>

      {/* Title Detail Modal */}
      <TitleModal
        showId={selectedTitleId}
        onClose={() => setSelectedTitleId(null)}
        onTitleClick={handleTitleClick}
      />
    </main>
  );
}
