"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useCompleteCrmActivity, useCrmFollowUps } from "@/lib/use-crm";

export default function CrmFollowUpsPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const { data, isLoading: listLoading, isError, error, refetch } = useCrmFollowUps();
  const complete = useCompleteCrmActivity();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleComplete(id: string) {
    try {
      await complete.mutateAsync(id);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  const now = new Date();

  return (
    <PlatformShell breadcrumb="Follow-ups">
      <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
        <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Follow-up Dashboard</h1>
        <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">
          Open reminders across every lead, soonest due first.
        </p>

        {isError && (
          <div className="mt-4">
            <ErrorState error={error} onRetry={() => refetch()} />
          </div>
        )}
        {!isError && !listLoading && data && data.length === 0 && (
          <div className="mt-4">
            <EmptyState title="Nothing due" hint="Follow-ups show here once a task has a due date." />
          </div>
        )}
        {data && data.length > 0 && (
          <ul className="mt-4 divide-y divide-[var(--bo-divider)]">
            {data.map((a) => {
              const overdue = a.due_at && new Date(a.due_at) < now;
              return (
                <li key={a.id} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <Link href={`/platform-admin/crm/${a.organization_id}`} className="font-medium text-[var(--bo-primary)]">
                      {a.summary}
                    </Link>
                    <p className={overdue ? "mt-0.5 text-xs text-[var(--bo-danger)]" : "mt-0.5 text-xs text-[var(--bo-text-muted)]"}>
                      {overdue ? "Overdue" : "Due"} {a.due_at && new Date(a.due_at).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => handleComplete(a.id)}
                    className="h-9 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm font-medium text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]"
                  >
                    Mark done
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </PlatformShell>
  );
}
