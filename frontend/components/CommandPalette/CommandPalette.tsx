"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Command } from "cmdk";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Search, Sparkles, Film, Tv, X, Hash, Clock } from "lucide-react";

interface CommandPaletteProps {
  genres: string[];
  recentTitles?: { id: string; title: string; type: string }[];
  onTitleSearch: (query: string) => void;
  onAISearch: (query: string) => void;
  onGenreSelect: (genre: string) => void;
  onTitleClick: (id: string) => void;
}

export function CommandPalette({
  genres,
  recentTitles = [],
  onTitleSearch,
  onAISearch,
  onGenreSelect,
  onTitleClick,
}: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const prefersReduced = useReducedMotion();
  const inputRef = useRef<HTMLInputElement>(null);

  // Global Cmd+K / Ctrl+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Close on Escape
  useEffect(() => {
    if (!open) setInputValue("");
  }, [open]);

  const handleSelect = useCallback(
    (value: string) => {
      setOpen(false);
      setInputValue("");

      if (value.startsWith("genre:")) {
        onGenreSelect(value.replace("genre:", ""));
      } else if (value.startsWith("ai:")) {
        const query = value.replace("ai:", "");
        onAISearch(query || inputValue);
      } else if (value.startsWith("search:")) {
        onTitleSearch(value.replace("search:", ""));
      } else if (value.startsWith("title:")) {
        onTitleClick(value.replace("title:", ""));
      }
    },
    [inputValue, onGenreSelect, onAISearch, onTitleSearch, onTitleClick]
  );

  return (
    <>
      {/* Trigger hint in nav (shown by parent via prop or as standalone) */}
      <button
        onClick={() => setOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/10 text-text-secondary hover:border-brand/30 hover:text-brand transition-all text-xs"
        aria-label="Open command palette"
      >
        <Search className="w-3.5 h-3.5" />
        <span>Command</span>
        <kbd className="ml-1 px-1.5 py-0.5 bg-bg-elevated rounded text-[10px] font-mono border border-white/10">⌘K</kbd>
      </button>

      {/* Palette overlay */}
      <AnimatePresence>
        {open && (
          <div className="fixed inset-0 z-[100]">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: prefersReduced ? 0 : 0.15 }}
              className="absolute inset-0 bg-black/70 backdrop-blur-md"
              onClick={() => setOpen(false)}
            />

            {/* Palette window */}
            <motion.div
              initial={prefersReduced ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={prefersReduced ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: -10 }}
              transition={{ duration: prefersReduced ? 0 : 0.18, ease: "easeOut" }}
              className="relative z-10 w-full max-w-2xl mx-auto mt-24 px-4"
            >
              <Command
                className="bg-bg-surface border border-white/12 rounded-2xl shadow-2xl overflow-hidden"
                onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); }}
                shouldFilter={true}
              >
                {/* Input */}
                <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/8">
                  <Search className="w-5 h-5 text-brand shrink-0" />
                  <Command.Input
                    ref={inputRef}
                    placeholder="Search titles, genres, or ask Cinevault…"
                    value={inputValue}
                    onValueChange={setInputValue}
                    className="flex-1 bg-transparent border-none outline-none text-text-primary placeholder:text-text-secondary text-base"
                    autoFocus
                  />
                  {inputValue && (
                    <button onClick={() => setInputValue("")} className="p-1 hover:bg-white/10 rounded-full">
                      <X className="w-4 h-4 text-text-secondary" />
                    </button>
                  )}
                  <kbd className="hidden md:block px-1.5 py-0.5 bg-bg-elevated rounded text-[10px] font-mono border border-white/10 text-text-secondary">ESC</kbd>
                </div>

                <Command.List className="max-h-[480px] overflow-y-auto p-2">
                  <Command.Empty className="py-10 text-center text-text-secondary text-sm">
                    No results. Try typing a title or genre.
                  </Command.Empty>

                  {/* AI Search action */}
                  {inputValue.length > 1 && (
                    <Command.Group heading="AI Search" className="[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-text-muted [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-2 [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider">
                      <Command.Item
                        value={`ai:${inputValue}`}
                        onSelect={handleSelect}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-colors data-[selected=true]:bg-brand/10 data-[selected=true]:text-brand group"
                      >
                        <Sparkles className="w-4 h-4 text-brand shrink-0" />
                        <div>
                          <span className="text-text-primary group-data-[selected=true]:text-brand">Ask Cinevault: </span>
                          <span className="text-brand">&ldquo;{inputValue}&rdquo;</span>
                        </div>
                      </Command.Item>
                    </Command.Group>
                  )}

                  {/* Keyword search action */}
                  {inputValue.length > 0 && (
                    <Command.Group heading="Quick Search">
                      <Command.Item
                        value={`search:${inputValue}`}
                        onSelect={handleSelect}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-colors data-[selected=true]:bg-brand/10 data-[selected=true]:text-brand"
                      >
                        <Search className="w-4 h-4 text-text-secondary shrink-0" />
                        <span className="text-text-primary">Search for &ldquo;{inputValue}&rdquo;</span>
                      </Command.Item>
                    </Command.Group>
                  )}

                  {/* Recently viewed */}
                  {recentTitles.length > 0 && (
                    <Command.Group heading="Recently Viewed">
                      {recentTitles.slice(0, 5).map((t) => (
                        <Command.Item
                          key={t.id}
                          value={`title:${t.id}`}
                          keywords={[t.title, t.type]}
                          onSelect={handleSelect}
                          className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-colors data-[selected=true]:bg-brand/10"
                        >
                          <Clock className="w-4 h-4 text-text-muted shrink-0" />
                          <span className="text-text-primary flex-1 truncate">{t.title}</span>
                          <span className="text-xs text-text-secondary flex-shrink-0">
                            {t.type === "Movie" ? <Film className="w-3 h-3" /> : <Tv className="w-3 h-3" />}
                          </span>
                        </Command.Item>
                      ))}
                    </Command.Group>
                  )}

                  {/* Genre jump */}
                  {genres.length > 0 && (
                    <Command.Group heading="Browse by Genre">
                      {genres.map((g) => (
                        <Command.Item
                          key={g}
                          value={`genre:${g}`}
                          keywords={[g]}
                          onSelect={handleSelect}
                          className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-colors data-[selected=true]:bg-brand/10 data-[selected=true]:text-brand"
                        >
                          <Hash className="w-4 h-4 text-text-secondary shrink-0" />
                          <span className="text-text-primary">{g}</span>
                        </Command.Item>
                      ))}
                    </Command.Group>
                  )}
                </Command.List>

                {/* Footer hints */}
                <div className="px-4 py-2.5 border-t border-white/8 flex items-center gap-4 text-[10px] text-text-muted">
                  <span><kbd className="font-mono">↑↓</kbd> navigate</span>
                  <span><kbd className="font-mono">↵</kbd> select</span>
                  <span><kbd className="font-mono">esc</kbd> close</span>
                  <div className="ml-auto flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-brand" />
                    <span className="text-brand">CineVault</span>
                  </div>
                </div>
              </Command>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
