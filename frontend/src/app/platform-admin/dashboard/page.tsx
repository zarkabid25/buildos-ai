"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Building2, DollarSign, Users } from "lucide-react";

import { ChartCard, UnavailableChartCard } from "@/components/platform/chart-card";
import { MetricCard } from "@/components/platform/metric-card";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { usePlatformDashboard } from "@/lib/use-platform";

function MetricSkeleton() {
  return (
    <div className="h-[158px] animate-pulse rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)]" />
  );
}

export default function PlatformDashboardPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { data, isLoading: statsLoading, isError, error, refetch } = usePlatformDashboard();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  const today = new Date();
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
  const dateRange = `${thirtyDaysAgo.toLocaleDateString(undefined, { month: "short", day: "numeric" })} - ${today.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;

  return (
    <PlatformShell breadcrumb="Overview">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.025em] text-[var(--bo-text)]">
            Good day, {admin.full_name.split(" ")[0]}
          </h1>
          <p className="mt-1 text-sm text-[var(--bo-text-secondary)]">
            Here&apos;s how BuildOS AI is doing across every company today.
          </p>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}

        {statsLoading && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <MetricSkeleton />
            <MetricSkeleton />
            <MetricSkeleton />
          </div>
        )}

        {data && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <MetricCard
              icon={<Building2 className="h-4 w-4" />}
              label="Active Companies"
              value={String(data.active_companies)}
              dateRange={`As of ${today.toLocaleDateString()}`}
              detailsHref="/platform-admin/companies"
            />
            <MetricCard
              icon={<Users className="h-4 w-4" />}
              label="Total Users"
              value={String(data.total_users)}
              dateRange={`As of ${today.toLocaleDateString()}`}
            />
            <MetricCard
              icon={<DollarSign className="h-4 w-4" />}
              label="New Companies"
              value={String(data.companies_created_last_30_days)}
              dateRange={dateRange}
              detailsHref="/platform-admin/companies"
            />
          </div>
        )}

        {data && data.pending_approval_companies > 0 && (
          <ChartCard title="Companies awaiting approval">
            <p className="text-sm text-[var(--bo-text-secondary)]">
              <span className="bo-tabular font-medium text-[#8A5B09]">{data.pending_approval_companies}</span>{" "}
              {data.pending_approval_companies === 1 ? "company hasn't" : "companies haven't"} been reviewed yet.{" "}
              <a href="/platform-admin/companies" className="font-medium text-[var(--bo-primary)]">
                Review in Companies
              </a>
              .
            </p>
          </ChartCard>
        )}

        {data && data.suspended_companies > 0 && (
          <ChartCard title="Suspended companies">
            <p className="text-sm text-[var(--bo-text-secondary)]">
              <span className="bo-tabular font-medium text-[var(--bo-danger)]">{data.suspended_companies}</span>{" "}
              {data.suspended_companies === 1 ? "company is" : "companies are"} currently suspended.{" "}
              <a href="/platform-admin/companies" className="font-medium text-[var(--bo-primary)]">
                Review in Companies
              </a>
              .
            </p>
          </ChartCard>
        )}

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <UnavailableChartCard
              title="Platform Revenue"
              reason="Needs the subscriptions/billing module (BUILD-149), which hasn't been built yet."
            />
          </div>
          <UnavailableChartCard
            title="Company Acquisition Sources"
            reason="Needs the CRM module (BUILD-146) to track where companies come from."
          />
        </div>
      </div>
    </PlatformShell>
  );
}
