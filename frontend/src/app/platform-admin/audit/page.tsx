"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { PlatformShell } from "@/components/platform-shell";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { usePlatformAuditLog } from "@/lib/use-platform";

export default function PlatformAuditLogPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { data, isLoading: logLoading, isError, error, refetch } = usePlatformAuditLog(!!admin);

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  return (
    <PlatformShell breadcrumb="Audit Log">
      <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
        <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Platform Audit Log</h1>
        <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">
          Every company approval, suspension and staff change, in order.
        </p>

        {isError && (
          <div className="mt-4">
            <ErrorState error={error} onRetry={() => refetch()} />
          </div>
        )}
        {!isError && !logLoading && data && data.length === 0 && (
          <div className="mt-4">
            <EmptyState title="No activity yet" />
          </div>
        )}
        {data && data.length > 0 && (
          <ul className="mt-4 divide-y divide-[var(--bo-divider)]">
            {data.map((entry) => (
              <li key={entry.id} className="py-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-[var(--bo-text)]">{entry.summary}</span>
                  <span className="bo-tabular text-xs text-[var(--bo-text-muted)]">
                    {new Date(entry.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-[var(--bo-text-muted)]">
                  {entry.actor_name ?? "Unknown"} &middot; {entry.action}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </PlatformShell>
  );
}
