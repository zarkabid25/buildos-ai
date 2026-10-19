"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, DollarSign, TrendingUp, Users2 } from "lucide-react";

import { MetricCard } from "@/components/platform/metric-card";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useRevenueDashboard } from "@/lib/use-platform-billing";

export default function PlatformBillingRevenuePage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { data, isLoading: revenueLoading, isError, error, refetch } = useRevenueDashboard();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  const maxTrend = data ? Math.max(1, ...data.monthly_trend.map((p) => Number(p.amount))) : 1;
  const totalPlans = data ? data.plan_distribution.reduce((sum, p) => sum + p.count, 0) : 0;

  return (
    <PlatformShell breadcrumb="Revenue">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.025em] text-[var(--bo-text)]">Revenue</h1>
          <p className="mt-1 text-sm text-[var(--bo-text-secondary)]">Recognized MRR, cash collected and outstanding balances -- all computed from real invoices and subscriptions, never estimated.</p>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {revenueLoading && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-32 rounded-[14px]" />)}
          </div>
        )}

        {data && (
          <>
            <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
              <MetricCard icon={<TrendingUp className="h-4 w-4" />} label="MRR" value={`$${data.mrr}`} dateRange="Active subscriptions only" />
              <MetricCard icon={<DollarSign className="h-4 w-4" />} label="Revenue Collected" value={`$${data.revenue_collected}`} dateRange="All-time, verified payments" />
              <MetricCard icon={<AlertTriangle className="h-4 w-4" />} label="Outstanding" value={`$${data.outstanding_amount}`} dateRange="Pending invoices" />
              <MetricCard icon={<Users2 className="h-4 w-4" />} label="Trialing / Grace" value={`${data.trialing_subscriptions} / ${data.grace_period_subscriptions}`} dateRange="Right now" />
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
                <h2 className="text-[15px] font-medium text-[var(--bo-text)]">Monthly revenue trend</h2>
                <p className="mt-0.5 text-xs text-[var(--bo-text-muted)]">Cash actually collected per month, from verified payments only.</p>
                {data.monthly_trend.length === 0 && <p className="mt-4 text-sm text-[var(--bo-text-muted)]">No payments verified yet.</p>}
                <div className="mt-4 space-y-2">
                  {data.monthly_trend.map((point) => (
                    <div key={point.month} className="flex items-center gap-3">
                      <span className="w-16 shrink-0 text-xs text-[var(--bo-text-muted)]">{point.month}</span>
                      <div className="h-6 flex-1 overflow-hidden rounded bg-[var(--bo-canvas)]">
                        <div
                          className="h-full rounded bg-[var(--bo-primary)]"
                          style={{ width: `${Math.max(2, (Number(point.amount) / maxTrend) * 100)}%` }}
                        />
                      </div>
                      <span className="bo-tabular w-20 shrink-0 text-right text-xs text-[var(--bo-text)]">${point.amount}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
                <h2 className="text-[15px] font-medium text-[var(--bo-text)]">Plan distribution</h2>
                <p className="mt-0.5 text-xs text-[var(--bo-text-muted)]">Companies with a live subscription, by plan ({totalPlans} total).</p>
                {data.plan_distribution.length === 0 && <p className="mt-4 text-sm text-[var(--bo-text-muted)]">No live subscriptions yet.</p>}
                <div className="mt-4 space-y-2">
                  {data.plan_distribution.map((p) => (
                    <div key={p.plan_name} className="flex items-center justify-between rounded-md border border-[var(--bo-divider)] px-3 py-2 text-sm">
                      <span className="text-[var(--bo-text)]">{p.plan_name}</span>
                      <span className="bo-tabular text-[var(--bo-text-muted)]">{p.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 text-xs text-[var(--bo-text-muted)]">
              <p>
                <strong className="text-[var(--bo-text-secondary)]">MRR</strong> counts only ACTIVE (paying) subscriptions -- trialing and grace-period subscriptions are excluded, since they aren't recognized revenue yet.{" "}
                <strong className="text-[var(--bo-text-secondary)]">Revenue Collected</strong> is real cash: the sum of invoices a staff member has actually verified.{" "}
                <strong className="text-[var(--bo-text-secondary)]">Outstanding</strong> is invoiced but unpaid -- a receivable, not revenue.
              </p>
            </div>
          </>
        )}
      </div>
    </PlatformShell>
  );
}
