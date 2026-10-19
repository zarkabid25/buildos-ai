"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useReplyAsStaff, useSupportTicketForStaff, useUpdateSupportTicket } from "@/lib/use-platform-support";
import type { SupportTicketPriority, SupportTicketStatus } from "@/lib/support-types";

export default function PlatformSupportTicketDetailPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useFeedback();
  const isReadOnly = admin?.role === "support";
  const { data: ticket, isLoading: ticketLoading, isError, error, refetch } = useSupportTicketForStaff(params.id);
  const updateTicket = useUpdateSupportTicket(params.id);
  const replyAsStaff = useReplyAsStaff(params.id);
  const [body, setBody] = useState("");
  const [isInternal, setIsInternal] = useState(false);

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleReply() {
    try {
      await replyAsStaff.mutateAsync({ body, is_internal: isInternal });
      setBody("");
      toast(isInternal ? "Internal note added." : "Reply sent.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleStatusChange(status: SupportTicketStatus) {
    try {
      await updateTicket.mutateAsync({ status });
      toast("Status updated.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handlePriorityChange(priority: SupportTicketPriority) {
    try {
      await updateTicket.mutateAsync({ priority });
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Support">
      <div className="max-w-2xl space-y-5">
        {ticketLoading && <Skeleton className="h-64 w-full" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {ticket && (
          <>
            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h1 className="text-[17px] font-medium text-[var(--bo-text)]">{ticket.subject}</h1>
              </div>
              <p className="mt-1 text-sm text-[var(--bo-text-muted)]">From {ticket.company_name ?? ticket.marketplace_supplier_name ?? "unknown"} &middot; {ticket.category}</p>
              {!isReadOnly && (
                <div className="mt-4 flex flex-wrap gap-3 border-t border-[var(--bo-divider)] pt-4">
                  <select value={ticket.status} onChange={(e) => handleStatusChange(e.target.value as SupportTicketStatus)} className="h-9 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-2 text-sm text-[var(--bo-text)]">
                    <option value="open">Open</option>
                    <option value="in_progress">In progress</option>
                    <option value="waiting_on_requester">Waiting on requester</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                  </select>
                  <select value={ticket.priority} onChange={(e) => handlePriorityChange(e.target.value as SupportTicketPriority)} className="h-9 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-2 text-sm text-[var(--bo-text)]">
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              )}
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <ul className="space-y-3">
                {ticket.messages.map((m) => (
                  <li key={m.id} className={`rounded-md border p-3 text-sm ${m.is_internal ? "border-amber-200 bg-amber-50" : m.author_type === "staff" ? "border-[var(--bo-primary)]/30 bg-[var(--bo-primary-soft)]" : "border-[var(--bo-divider)] bg-[var(--bo-canvas)]"}`}>
                    <div className="flex items-center justify-between">
                      <p className="text-[var(--bo-text)]">{m.body}</p>
                      {m.is_internal && <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">Internal</span>}
                    </div>
                    <p className="mt-1 text-xs text-[var(--bo-text-muted)]">{m.author_name ?? m.author_type} &middot; {new Date(m.created_at).toLocaleString()}</p>
                  </li>
                ))}
              </ul>

              {!isReadOnly && (
                <div className="mt-4 space-y-2 border-t border-[var(--bo-divider)] pt-4">
                  <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={3} placeholder="Write a reply or internal note..." className="w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 py-2 text-sm text-[var(--bo-text)]" />
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1.5 text-sm text-[var(--bo-text)]">
                      <input type="checkbox" checked={isInternal} onChange={(e) => setIsInternal(e.target.checked)} /> Internal note (never shown to the requester)
                    </label>
                    <button onClick={handleReply} disabled={!body || replyAsStaff.isPending} className="h-9 rounded-md bg-[var(--bo-primary)] px-4 text-sm font-medium text-[var(--bo-on-primary)] hover:bg-[var(--bo-primary-hover)] disabled:opacity-50">
                      {replyAsStaff.isPending ? "Sending..." : isInternal ? "Add note" : "Send reply"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </PlatformShell>
  );
}
