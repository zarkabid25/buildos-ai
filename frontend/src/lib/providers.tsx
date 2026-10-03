"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { FeedbackProvider, useFeedback } from "@/components/feedback";
import { ApiError } from "@/lib/api";
import { AuthProvider } from "@/lib/auth-context";

declare module "@tanstack/react-query" {
  interface Register {
    // inlineError: the page catches this mutation's error and shows it next to the form.
    mutationMeta: { inlineError?: boolean };
  }
}

function QueryProvider({ children }: { children: ReactNode }) {
  const { toast } = useFeedback();
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // A 4xx (not found, forbidden, invalid) won't fix itself on retry, and three
            // retries on a dead server keep a spinner up for ~30s before the error shows.
            retry: (failureCount, error) =>
              error instanceof ApiError && error.status < 500 ? false : failureCount < 1,
          },
        },
        // Any failed save/delete is reported, so nothing fails silently (BUILD-117).
        mutationCache: new MutationCache({
          onError: (error, _vars, _ctx, mutation) => {
            if (mutation.options.meta?.inlineError) return;
            toast(error instanceof ApiError ? error.message : "Something went wrong. Please try again.", "error");
          },
        }),
      })
  );
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <FeedbackProvider>
      <QueryProvider>
        <AuthProvider>{children}</AuthProvider>
      </QueryProvider>
    </FeedbackProvider>
  );
}
