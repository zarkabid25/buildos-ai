"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, DollarSign, FileWarning, Truck } from "lucide-react";

import { MetricCard } from "@/components/platform/metric-card";
import { CommissionsSubNav } from "@/components/platform/commissions-subnav";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useCommissionRevenueDashboard } from "@/lib/use-commissions";

export default function PlatformCommissionsOverviewPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { data, isLoading: revenueLoading, isError, error, refetch } = useCommissionRevenueDashboard();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  return (
    <PlatformShell breadcrumb="Commissions">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.025em] text-[var(--bo-text)]">Marketplace Commissions</h1>
          <p className="mt-1 text-sm text-[var(--bo-text-secondary)]">BuildOS AI's second revenue stream -- supplier commercial agreements and the commission ledger, kept entirely separate from SaaS billing.</p>
        </div>

        <CommissionsSubNav />

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {revenueLoading && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-32 rounded-[14px]" />)}
          </div>
        )}
        {data && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
            <MetricCard icon={<DollarSign className="h-4 w-4" />} label="Commission Earned" value={`$${data.commission_earned}`} dateRange="All-time, net of reversals" />
            <MetricCard icon={<FileWarning className="h-4 w-4" />} label="Outstanding" value={`$${data.outstanding_commission}`} dateRange="Invoiced, not yet collected" />
            <MetricCard icon={<Truck className="h-4 w-4" />} label="Attributed Orders" value={String(data.marketplace_attributed_order_count)} dateRange={`$${data.marketplace_attributed_order_value} order value`} />
            <MetricCard icon={<AlertTriangle className="h-4 w-4" />} label="Disputed" value={`$${data.disputed_amount}`} dateRange={`${data.active_agreements} active agreement(s)`} />
          </div>
        )}
      </div>
    </PlatformShell>
  );
}
