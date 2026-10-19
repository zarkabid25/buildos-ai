"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CommissionsSubNav } from "@/components/platform/commissions-subnav";
import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useCommissionDisputes, useReviewDispute } from "@/lib/use-commissions";
import type { CommissionDisputeStatus } from "@/lib/commission-types";

const STATUS_CLASSES: Record<string, string> = {
  open: "bg-amber-50 text-[var(--bo-warning)]",
  approved: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  rejected: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
};

export default function PlatformCommissionDisputesPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast, confirm } = useFeedback();
  const isReadOnly = admin?.role === "support";

  const [status, setStatus] = useState<CommissionDisputeStatus | "">("open");
  const { data: disputes, isLoading: disputesLoading, isError, error, refetch } = useCommissionDisputes({ status: status || undefined });
  const reviewDispute = useReviewDispute();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleReview(disputeId: string, approve: boolean) {
    const ok = await confirm({
      title: approve ? "Approve this dispute?" : "Reject this dispute?",
      body: approve ? "This posts a full reversal of the original commission charge." : "The original charge stays as it is.",
      confirmLabel: approve ? "Approve" : "Reject",
      danger: !approve,
    });
    if (!ok) return;
    const resolution_notes = window.prompt("Resolution notes (required):");
    if (!resolution_notes) return;
    try {
      await reviewDispute.mutateAsync({ disputeId, approve, resolution_notes });
      toast(approve ? "Dispute approved and reversed." : "Dispute rejected.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Commissions">
      <div className="space-y-5">
        <CommissionsSubNav />

        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Commission Disputes</h1>
              <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">Approving never edits the original charge -- it posts a new reversal entry.</p>
            </div>
            <select value={status} onChange={(e) => setStatus(e.target.value as CommissionDisputeStatus | "")} className="h-10 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]">
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {!disputesLoading && disputes && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Reason</th>
                  <th className="px-4 py-3">Raised by</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Resolution</th>
                  {!isReadOnly && <th className="px-4 py-3"></th>}
                </tr>
              </thead>
              <tbody>
                {disputes.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-[var(--bo-text-muted)]">No disputes in this view.</td></tr>
                )}
                {disputes.map((d) => (
                  <tr key={d.id} className="border-t border-[var(--bo-divider)]">
                    <td className="max-w-xs px-4 py-3 text-[var(--bo-text)]">{d.reason}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{d.raised_by_staff_name ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[d.status]}`}>{d.status}</span>
                    </td>
                    <td className="max-w-xs px-4 py-3 text-[var(--bo-text-muted)]">{d.resolution_notes ?? "—"}</td>
                    {!isReadOnly && (
                      <td className="px-4 py-3 text-right">
                        {d.status === "open" && (
                          <div className="flex justify-end gap-2">
                            <button onClick={() => handleReview(d.id, true)} className="text-xs font-medium text-[var(--bo-success)] hover:underline">Approve</button>
                            <button onClick={() => handleReview(d.id, false)} className="text-xs font-medium text-[var(--bo-danger)] hover:underline">Reject</button>
                          </div>
                        )}
                      </td>
                    )}
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
