"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, DollarSign, FileWarning, TrendingUp } from "lucide-react";

import { CommissionsSubNav } from "@/components/platform/commissions-subnav";
import { MetricCard } from "@/components/platform/metric-card";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useCommissionRevenueDashboard } from "@/lib/use-commissions";

export default function PlatformCommissionRevenuePage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { data, isLoading: revenueLoading, isError, error, refetch } = useCommissionRevenueDashboard();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  const maxTrend = data ? Math.max(1, ...data.monthly_trend.map((p) => Math.abs(Number(p.amount)))) : 1;

  return (
    <PlatformShell breadcrumb="Commissions">
      <div className="space-y-5">
        <CommissionsSubNav />

        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.025em] text-[var(--bo-text)]">Commission Revenue</h1>
          <p className="mt-1 text-sm text-[var(--bo-text-secondary)]">Earned, invoiced, collected and outstanding -- kept distinct. The marketplace order value itself is never counted as BuildOS revenue.</p>
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
              <MetricCard icon={<TrendingUp className="h-4 w-4" />} label="Earned" value={`$${data.commission_earned}`} dateRange="All-time accruals, net of reversals" />
              <MetricCard icon={<DollarSign className="h-4 w-4" />} label="Invoiced" value={`$${data.commission_invoiced}`} dateRange="Billed to suppliers" />
              <MetricCard icon={<DollarSign className="h-4 w-4" />} label="Collected" value={`$${data.commission_collected}`} dateRange="Actually received" />
              <MetricCard icon={<FileWarning className="h-4 w-4" />} label="Outstanding" value={`$${data.outstanding_commission}`} dateRange="Invoiced, unpaid" />
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
                <h2 className="text-[15px] font-medium text-[var(--bo-text)]">Monthly commission trend</h2>
                <p className="mt-0.5 text-xs text-[var(--bo-text-muted)]">Net accrual per month (accruals minus reversals/adjustments).</p>
                {data.monthly_trend.length === 0 && <p className="mt-4 text-sm text-[var(--bo-text-muted)]">No commission activity yet.</p>}
                <div className="mt-4 space-y-2">
                  {data.monthly_trend.map((point) => {
                    const amt = Number(point.amount);
                    return (
                      <div key={point.month} className="flex items-center gap-3">
                        <span className="w-16 shrink-0 text-xs text-[var(--bo-text-muted)]">{point.month}</span>
                        <div className="h-6 flex-1 overflow-hidden rounded bg-[var(--bo-canvas)]">
                          <div
                            className={`h-full rounded ${amt < 0 ? "bg-[var(--bo-danger)]" : "bg-[var(--bo-primary)]"}`}
                            style={{ width: `${Math.max(2, (Math.abs(amt) / maxTrend) * 100)}%` }}
                          />
                        </div>
                        <span className="bo-tabular w-20 shrink-0 text-right text-xs text-[var(--bo-text)]">${point.amount}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
                <h2 className="text-[15px] font-medium text-[var(--bo-text)]">Supplier revenue contribution</h2>
                <p className="mt-0.5 text-xs text-[var(--bo-text-muted)]">Net commission earned per supplier, all-time.</p>
                {data.supplier_contributions.length === 0 && <p className="mt-4 text-sm text-[var(--bo-text-muted)]">No contributions yet.</p>}
                <div className="mt-4 space-y-2">
                  {data.supplier_contributions.map((c) => (
                    <div key={c.marketplace_supplier_id} className="flex items-center justify-between rounded-md border border-[var(--bo-divider)] px-3 py-2 text-sm">
                      <span className="text-[var(--bo-text)]">{c.marketplace_supplier_name}</span>
                      <span className="bo-tabular text-[var(--bo-text-muted)]">${c.commission_earned}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {Number(data.disputed_amount) !== 0 && (
              <div className="flex items-center gap-2 rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-4 text-sm text-[var(--bo-warning)]">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                ${data.disputed_amount} currently under open dispute -- see the Disputes tab.
              </div>
            )}

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 text-xs text-[var(--bo-text-muted)]">
              <p>
                <strong className="text-[var(--bo-text-secondary)]">Earned</strong> is every accrual, reversal and adjustment ever posted, net.{" "}
                <strong className="text-[var(--bo-text-secondary)]">Invoiced</strong> is what has been billed to suppliers via a commission invoice.{" "}
                <strong className="text-[var(--bo-text-secondary)]">Collected</strong> is real cash a staff member has recorded as received.{" "}
                <strong className="text-[var(--bo-text-secondary)]">Outstanding</strong> is invoiced minus collected -- a receivable.
                None of these ever includes the marketplace order's own value ({`$${data.marketplace_attributed_order_value}`} across {data.marketplace_attributed_order_count} attributed order(s)), which belongs to the company and supplier, not BuildOS.
              </p>
            </div>
          </>
        )}
      </div>
    </PlatformShell>
  );
}
