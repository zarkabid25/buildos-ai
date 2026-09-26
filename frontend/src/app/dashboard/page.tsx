"use client";

import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { InsightsList, RulesNote } from "@/components/insights-list";
import { useAuth } from "@/lib/auth-context";
import { useInsights } from "@/lib/use-ai";
import { useProjectSummary } from "@/lib/use-projects";
import { formatCurrency } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const { data: summary, isLoading: summaryLoading } = useProjectSummary();
  const { data: insights } = useInsights();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) return null;

  const firstName = user.full_name.split(" ")[0];

  const stats = [
    { label: "Projects", value: summary ? String(summary.total_projects) : "—" },
    { label: "Project Value", value: summary ? formatCurrency(summary.total_budget) : "—" },
    { label: "Avg Progress", value: summary ? `${summary.avg_progress}%` : "—" },
    { label: "At Risk", value: summary ? String(summary.at_risk_count) : "—" },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Good morning, {firstName}</h1>
          <p className="text-muted">Here&apos;s what&apos;s happening across your construction business.</p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label} className="rounded-card border border-border bg-surface p-4">
              <div className="text-2xl font-semibold text-ink">
                {summaryLoading ? "…" : stat.value}
              </div>
              <div className="text-sm text-muted">{stat.label}</div>
            </div>
          ))}
        </div>

        <div className="rounded-card border border-border bg-surface p-5">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">Executive Summary</h2>
            <Link href="/ai-insights" className="text-xs text-primary hover:underline">
              View all insights
            </Link>
          </div>
          {insights ? (
            <>
              <p className="mb-1 text-sm text-ink">{insights.summary}</p>
              <RulesNote />
              <div className="mt-2">
                <InsightsList insights={insights.insights} limit={3} />
              </div>
            </>
          ) : (
            <p className="text-sm text-muted">Checking your projects...</p>
          )}
          <Link href="/ai" className="mt-3 inline-block text-xs text-primary hover:underline">
            Ask BuildOS AI a question
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
