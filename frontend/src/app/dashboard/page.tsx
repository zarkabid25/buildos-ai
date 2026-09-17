"use client";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { useProjectSummary } from "@/lib/use-projects";
import { formatCurrency } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const { data: summary, isLoading: summaryLoading } = useProjectSummary();

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
          <h2 className="mb-2 text-sm font-semibold text-ink">AI Executive Summary</h2>
          <p className="text-sm text-muted">
            {summary && summary.total_projects > 0
              ? `${summary.at_risk_count} of ${summary.total_projects} projects need attention. AI-generated risk explanations arrive with the AI Copilot in a later build.`
              : "No data yet. Create your first project to get AI-powered insights here."}
          </p>
        </div>
      </div>
    </AppShell>
  );
}
