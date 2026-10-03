"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { SEARCH_SECTIONS, useGlobalSearch, type SearchResultItem } from "@/lib/use-search";

export function GlobalSearch() {
  const [raw, setRaw] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const { data, isFetching } = useGlobalSearch(debounced);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(raw), 250);
    return () => clearTimeout(t);
  }, [raw]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(item: SearchResultItem) {
    setOpen(false);
    setRaw("");
    router.push(item.link);
  }

  const showDropdown = open && raw.trim().length >= 2;
  const nothingFound = data && data.total === 0 && !isFetching;

  return (
    <div className="relative w-full max-w-sm" ref={containerRef}>
      <input
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        onFocus={() => setOpen(true)}
        placeholder="Search projects, tasks, materials..."
        className="h-8 w-full rounded-md border border-border bg-background px-3 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/30"
      />

      {showDropdown && (
        <div className="absolute left-0 top-9 z-20 max-h-96 w-96 max-w-[calc(100vw-2rem)] overflow-y-auto rounded-card border border-border bg-surface shadow-lg">
          {isFetching && <p className="px-3 py-4 text-sm text-muted">Searching...</p>}
          {nothingFound && <p className="px-3 py-4 text-sm text-muted">No matches for &ldquo;{debounced}&rdquo;.</p>}
          {data &&
            SEARCH_SECTIONS.map(({ key, label }) => {
              const items = data[key] as SearchResultItem[];
              if (!items || items.length === 0) return null;
              return (
                <div key={key} className="border-b border-border py-1 last:border-0">
                  <div className="px-3 py-1 text-xs font-medium uppercase tracking-wide text-muted">
                    {label}
                  </div>
                  {items.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleSelect(item)}
                      className="block w-full px-3 py-1.5 text-left text-sm hover:bg-gray-50"
                    >
                      <span className="text-ink">{item.title}</span>
                      {item.subtitle && <span className="ml-2 text-xs text-muted">{item.subtitle}</span>}
                    </button>
                  ))}
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
