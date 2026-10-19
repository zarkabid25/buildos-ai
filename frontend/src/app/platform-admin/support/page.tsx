"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PlatformShell } from "@/components/platform-shell";
import { ErrorState, TableSkeleton } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useAllSupportTickets } from "@/lib/use-platform-support";
import type { SupportTicketStatus } from "@/lib/support-types";

const STATUS_CLASSES: Record<string, string> = {
  open: "bg-amber-50 text-[var(--bo-warning)]",
  in_progress: "bg-blue-50 text-[var(--bo-primary)]",
  waiting_on_requester: "bg-amber-50 text-[var(--bo-warning)]",
  resolved: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  closed: "bg-gray-100 text-[var(--bo-text-muted)]",
};

export default function PlatformSupportPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const [status, setStatus] = useState<SupportTicketStatus | "">("");
  const { data, isLoading: listLoading, isError, error, refetch } = useAllSupportTickets(status || undefined);

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  return (
    <PlatformShell breadcrumb="Support">
      <div className="space-y-5">
        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Support Desk</h1>
              <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">Tickets from both companies and marketplace suppliers.</p>
            </div>
            <select value={status} onChange={(e) => setStatus(e.target.value as SupportTicketStatus | "")} className="h-10 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]">
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In progress</option>
              <option value="waiting_on_requester">Waiting on requester</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {listLoading && <TableSkeleton rows={4} />}
        {data && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">From</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-[var(--bo-text-muted)]">No tickets in this view.</td></tr>
                )}
                {data.map((t) => (
                  <tr key={t.id} className="h-14 border-t border-[var(--bo-divider)] hover:bg-[var(--bo-surface-hover)]">
                    <td className="px-4 py-3">
                      <Link href={`/platform-admin/support/${t.id}`} className="font-medium text-[var(--bo-primary)] hover:underline">{t.subject}</Link>
                    </td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{t.company_name ?? t.marketplace_supplier_name ?? "—"}</td>
                    <td className="px-4 py-3 capitalize text-[var(--bo-text-muted)]">{t.category}</td>
                    <td className="px-4 py-3 capitalize text-[var(--bo-text-muted)]">{t.priority}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_CLASSES[t.status]}`}>{t.status.replace(/_/g, " ")}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </PlatformShell>
  );
}
