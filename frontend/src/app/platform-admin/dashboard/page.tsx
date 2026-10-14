"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { PlatformShell } from "@/components/platform-shell";
import { Card } from "@/components/ui/card";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { usePlatformDashboard } from "@/lib/use-platform";

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
    </Card>
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

  return (
    <PlatformShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-ink">Business Dashboard</h1>
          <p className="text-sm text-muted">Signed in as {admin.full_name}</p>
        </div>

        {statsLoading && (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => (
              <Card key={i}>
                <Skeleton className="h-4 w-20" />
                <Skeleton className="mt-2 h-7 w-12" />
              </Card>
            ))}
          </div>
        )}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {data && (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Active companies" value={String(data.active_companies)} />
            <StatCard label="Suspended companies" value={String(data.suspended_companies)} />
            <StatCard label="Total users" value={String(data.total_users)} />
            <StatCard label="New companies (30d)" value={String(data.companies_created_last_30_days)} />
          </div>
        )}

        <Card>
          <p className="text-sm font-medium text-ink">Not available yet</p>
          <p className="mt-1 text-sm text-muted">
            Monthly recurring revenue, CRM leads and supplier verification counts need the subscriptions,
            CRM and marketplace modules, which haven&apos;t been built yet. They&apos;ll appear here once those
            exist, rather than being shown as estimated or placeholder numbers now.
          </p>
        </Card>
      </div>
    </PlatformShell>
  );
}
