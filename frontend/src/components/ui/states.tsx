import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

// Shared loading / empty / error states (BUILD-114..117), so "still loading",
// "nothing here yet" and "couldn't load" never look the same.

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded bg-gray-100", className)} />;
}

export function TableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <Card className="space-y-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-5 w-full" />
      ))}
    </Card>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <Card className="py-8 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </Card>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message =
    error instanceof ApiError
      ? error.message
      : "Couldn't reach the server. Check your connection and try again.";
  return (
    <Card role="alert" className="flex flex-wrap items-center justify-between gap-3 border-danger/30">
      <div>
        <p className="text-sm font-medium text-danger">This couldn&apos;t be loaded</p>
        <p className="text-sm text-muted">{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      )}
    </Card>
  );
}

interface QueryLike<T> {
  data: T | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
}

/** Renders a query's loading, error and empty states, then `children(data)`. */
export function QueryView<T>({
  query,
  isEmpty,
  empty,
  loading,
  children,
}: {
  query: QueryLike<T>;
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
  loading?: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (query.isLoading) return <>{loading ?? <TableSkeleton />}</>;
  if (query.isError || query.data === undefined) {
    return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  }
  if (isEmpty?.(query.data) && empty) return <>{empty}</>;
  return <>{children(query.data)}</>;
}
