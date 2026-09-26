"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { InsightsList, RulesNote } from "@/components/insights-list";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";
import { useInsights } from "@/lib/use-ai";

export default function AiInsightsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const { data, isLoading } = useInsights();

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">AI Insights</h1>
          <p className="text-muted">What needs attention across schedule, cost, inventory, equipment and procurement.</p>
        </div>

        <Card>
          {isLoading && <p className="text-sm text-muted">Checking your projects...</p>}
          {data && (
            <>
              <div className="mb-4 grid grid-cols-3 gap-3">
                {(["high", "medium", "low"] as const).map((sev) => (
                  <div key={sev} className="rounded-md border border-border p-3">
                    <div className="text-2xl font-semibold text-ink">{data.counts[sev] ?? 0}</div>
                    <div className="text-xs uppercase text-muted">{sev}</div>
                  </div>
                ))}
              </div>
              <p className="mb-2 text-sm text-ink">{data.summary}</p>
              <RulesNote />
              <div className="mt-2">
                <InsightsList insights={data.insights} />
              </div>
            </>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
