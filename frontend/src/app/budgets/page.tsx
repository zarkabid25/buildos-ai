"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { EmptyState, QueryView } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import type { ProjectReport } from "@/lib/report-types";
import { useReport } from "@/lib/use-reports";
import { formatCurrency } from "@/lib/utils";

function UsedBar({ spent, committed, budget }: { spent: number; committed: number; budget: number }) {
  if (budget <= 0) return <span className="text-xs text-muted">No budget set</span>;
  const pct = (n: number) => `${Math.min(100, (n / budget) * 100)}%`;
  const used = Math.round(((spent + committed) / budget) * 100);
  return (
    <div className="w-40">
      <div className="flex h-2 overflow-hidden rounded-full bg-gray-100">
        <div className="h-2 bg-primary" style={{ width: pct(spent) }} title="Spent" />
        <div className="h-2 bg-blue-300" style={{ width: pct(committed) }} title="Committed (POs)" />
      </div>
      <div className={`mt-1 text-xs ${used > 100 ? "font-medium text-danger" : "text-muted"}`}>{used}% used or committed</div>
    </div>
  );
}

export default function BudgetsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  // Same numbers as each project's Costs tab and the project report, so they can't disagree.
  const query = useReport<ProjectReport>("projects", {});

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Budgets</h1>
          <p className="text-muted">Budget against spending and commitments for every project.</p>
        </div>

        <QueryView
          query={query}
          isEmpty={(r) => r.rows.length === 0}
          empty={<EmptyState title="No projects yet" hint="A project's budget is set when it's created." />}
        >
          {(report) => {
            const overForecast = report.rows.filter((r) => Number(r.expected_variance) > 0).length;
            const remaining = Number(report.total_budget) - Number(report.total_committed) - Number(report.total_actual);
            return (
              <>
                <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                  {[
                    { label: "Total budget", value: formatCurrency(report.total_budget) },
                    { label: "Committed (POs)", value: formatCurrency(report.total_committed) },
                    { label: "Spent", value: formatCurrency(report.total_actual) },
                    { label: "Remaining", value: formatCurrency(remaining) },
                  ].map((s) => (
                    <Card key={s.label}>
                      <div className="text-xs uppercase tracking-wide text-muted">{s.label}</div>
                      <div className="text-xl font-semibold text-ink">{s.value}</div>
                    </Card>
                  ))}
                </div>
                {overForecast > 0 && (
                  <p className="text-sm text-danger">
                    {overForecast} project{overForecast === 1 ? " is" : "s are"} forecast to finish over budget.
                  </p>
                )}
                <Card className="overflow-x-auto p-0">
                  <table className="w-full whitespace-nowrap text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                        <th className="px-4 py-3 font-medium">Project</th>
                        <th className="px-4 py-3 font-medium">Budget</th>
                        <th className="px-4 py-3 font-medium">Spent</th>
                        <th className="px-4 py-3 font-medium">Committed</th>
                        <th className="px-4 py-3 font-medium">Used</th>
                        <th className="px-4 py-3 font-medium">Forecast</th>
                        <th className="px-4 py-3 font-medium">Variance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.rows.map((r) => {
                        const over = Number(r.expected_variance) > 0;
                        return (
                          <tr key={r.project_id} className="border-b border-border last:border-0">
                            <td className="px-4 py-3">
                              <Link href={`/project-costs?project=${r.project_id}`} className="font-medium text-primary hover:underline">
                                {r.name}
                              </Link>
                              <span className="ml-1 text-xs text-muted">{r.progress_percent}% done</span>
                            </td>
                            <td className="px-4 py-3">{formatCurrency(r.budget)}</td>
                            <td className="px-4 py-3">{formatCurrency(r.actual)}</td>
                            <td className="px-4 py-3">{formatCurrency(r.committed)}</td>
                            <td className="px-4 py-3">
                              <UsedBar spent={Number(r.actual)} committed={Number(r.committed)} budget={Number(r.budget)} />
                            </td>
                            <td className="px-4 py-3">{formatCurrency(r.forecast)}</td>
                            <td className={`px-4 py-3 ${over ? "text-danger" : "text-success"}`}>
                              {over ? "+" : ""}
                              {formatCurrency(r.expected_variance)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </Card>
                <p className="text-xs text-muted">
                  Forecast extrapolates spending from reported progress; before any progress is recorded it&apos;s just what&apos;s
                  committed plus spent. Click a project for its full cost breakdown.
                </p>
              </>
            );
          }}
        </QueryView>
      </div>
    </AppShell>
  );
}
