"use client";

import { Fragment, useEffect, useState, type ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { useDocumentSearch, type DocumentSearchHit } from "@/lib/use-documents";

/** Wrap each search term in <mark>, without injecting HTML. */
function highlight(text: string, terms: string[]): ReactNode {
  if (terms.length === 0) return text;
  const escaped = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "gi"));
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <mark key={i} className="rounded bg-amber-100 px-0.5 text-ink">
        {part}
      </mark>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    )
  );
}

export function DocumentSearch({ onOpen }: { onOpen: (hit: DocumentSearchHit) => void }) {
  const [input, setInput] = useState("");
  const [q, setQ] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setQ(input), 300);
    return () => clearTimeout(t);
  }, [input]);
  const query = useDocumentSearch(q);
  const active = q.trim().length >= 2;

  return (
    <Card className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-ink">Search inside documents</h2>
        <p className="text-xs text-muted">
          Finds passages containing all your words in PDFs, Word, Excel, text and CSV files. Scanned images have no text to search.
        </p>
      </div>
      <Input
        aria-label="Search inside documents"
        placeholder="e.g. retention money, liquidated damages, concrete grade"
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      {active && query.isLoading && (
        <div className="space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      )}
      {active && query.isError && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {active && query.data && query.data.length === 0 && (
        <p className="text-sm text-muted">No document contains all of those words.</p>
      )}
      {active && query.data && query.data.length > 0 && (
        <ul className="divide-y divide-border">
          {query.data.map((hit, i) => (
            <li key={`${hit.document_id}-${hit.page}-${i}`} className="py-2">
              <button className="text-left text-sm font-medium text-primary hover:underline" onClick={() => onOpen(hit)}>
                {hit.title}
              </button>
              <span className="ml-2 text-xs text-muted">
                {hit.page ? `page ${hit.page}` : ""}
                {hit.project_name ? `${hit.page ? " · " : ""}${hit.project_name}` : ""}
              </span>
              <p className="mt-0.5 text-sm text-ink">{highlight(hit.snippet, hit.terms)}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
