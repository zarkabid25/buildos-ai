"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useReviewSupplierApplication, useSupplierApplication, useSupplierApplicationDocuments } from "@/lib/use-platform-support";

export default function PlatformSupplierApplicationDetailPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast, confirm } = useFeedback();
  const isReadOnly = admin?.role === "support";
  const { data: application, isLoading: appLoading, isError, error, refetch } = useSupplierApplication(params.id);
  const documentsQuery = useSupplierApplicationDocuments(params.id);
  const review = useReviewSupplierApplication(params.id);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleReview(approve: boolean) {
    if (!notes) {
      toast("Review notes are required.", "error");
      return;
    }
    const ok = await confirm({
      title: approve ? "Approve this application?" : "Reject this application?",
      body: approve ? "This creates a new marketplace supplier, still pending verification -- never auto-verified." : "The applicant will not be onboarded.",
      confirmLabel: approve ? "Approve" : "Reject",
      danger: !approve,
    });
    if (!ok) return;
    try {
      await review.mutateAsync({ approve, review_notes: notes });
      toast(approve ? "Application approved. A pending supplier record was created." : "Application rejected.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Supplier Applications">
      <div className="max-w-2xl space-y-5">
        {appLoading && <Skeleton className="h-64 w-full" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {application && (
          <>
            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h1 className="text-[17px] font-medium text-[var(--bo-text)]">{application.business_name}</h1>
                <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium capitalize text-[var(--bo-warning)]">{application.status}</span>
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div><dt className="text-xs text-[var(--bo-text-muted)]">Contact</dt><dd className="text-[var(--bo-text)]">{application.contact_name}</dd></div>
                <div><dt className="text-xs text-[var(--bo-text-muted)]">Email</dt><dd className="text-[var(--bo-text)]">{application.email}</dd></div>
                <div><dt className="text-xs text-[var(--bo-text-muted)]">Phone</dt><dd className="text-[var(--bo-text)]">{application.phone ?? "—"}</dd></div>
                <div><dt className="text-xs text-[var(--bo-text-muted)]">Registration info</dt><dd className="text-[var(--bo-text)]">{application.business_registration_info ?? "—"}</dd></div>
                <div><dt className="text-xs text-[var(--bo-text-muted)]">Categories</dt><dd className="text-[var(--bo-text)]">{application.categories.join(", ") || "—"}</dd></div>
                <div><dt className="text-xs text-[var(--bo-text-muted)]">Delivery locations</dt><dd className="text-[var(--bo-text)]">{application.delivery_locations.join(", ") || "—"}</dd></div>
              </dl>
              {application.business_description && <p className="mt-3 text-sm text-[var(--bo-text-secondary)]">{application.business_description}</p>}
            </div>

            {documentsQuery.data && documentsQuery.data.length > 0 && (
              <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
                <h2 className="text-sm font-semibold text-[var(--bo-text)]">Documents</h2>
                <ul className="mt-2 space-y-1">
                  {documentsQuery.data.map((d) => (
                    <li key={d.id} className="text-sm text-[var(--bo-text-secondary)]">{d.title} ({(d.size_bytes / 1024).toFixed(0)} KB)</li>
                  ))}
                </ul>
              </div>
            )}

            {application.status === "pending" && !isReadOnly && (
              <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
                <h2 className="text-sm font-semibold text-[var(--bo-text)]">Review</h2>
                <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="Review notes (required)" className="mt-2 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 py-2 text-sm text-[var(--bo-text)]" />
                <div className="mt-3 flex gap-2">
                  <button onClick={() => handleReview(true)} disabled={review.isPending} className="h-10 rounded-md bg-[var(--bo-success)] px-4 text-sm font-medium text-white disabled:opacity-50">Approve</button>
                  <button onClick={() => handleReview(false)} disabled={review.isPending} className="h-10 rounded-md border border-[var(--bo-border)] px-4 text-sm font-medium text-[var(--bo-danger)]">Reject</button>
                </div>
              </div>
            )}

            {application.status !== "pending" && (
              <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 text-sm text-[var(--bo-text-secondary)] shadow-[var(--bo-shadow-card)]">
                Reviewed by {application.reviewed_by_staff_name ?? "staff"}: {application.review_notes}
                {application.marketplace_supplier_id && <p className="mt-1 text-xs text-[var(--bo-text-muted)]">Created marketplace supplier (still pending verification).</p>}
              </div>
            )}
          </>
        )}
      </div>
    </PlatformShell>
  );
}
