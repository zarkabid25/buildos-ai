"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PlatformShell } from "@/components/platform-shell";
import { ErrorState, TableSkeleton } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useSupplierApplications } from "@/lib/use-platform-support";

const STATUS_CLASSES: Record<string, string> = {
  pending: "bg-amber-50 text-[var(--bo-warning)]",
  approved: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  rejected: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
};

export default function PlatformSupplierApplicationsPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const [status, setStatus] = useState("pending");
  const { data, isLoading: listLoading, isError, error, refetch } = useSupplierApplications(status || undefined);

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  return (
    <PlatformShell breadcrumb="Supplier Applications">
      <div className="space-y-5">
        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Supplier Applications</h1>
              <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">Public "become a supplier" submissions, awaiting review.</p>
            </div>
            <select value={status} onChange={(e) => setStatus(e.target.value)} className="h-10 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]">
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
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
                  <th className="px-4 py-3">Business</th>
                  <th className="px-4 py-3">Contact</th>
                  <th className="px-4 py-3">Categories</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {data.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-[var(--bo-text-muted)]">No applications in this view.</td></tr>
                )}
                {data.map((a) => (
                  <tr key={a.id} className="h-14 border-t border-[var(--bo-divider)] hover:bg-[var(--bo-surface-hover)]">
                    <td className="px-4 py-3 font-medium text-[var(--bo-text)]">{a.business_name}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{a.contact_name} &middot; {a.email}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{a.categories.join(", ") || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_CLASSES[a.status]}`}>{a.status}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/platform-admin/supplier-applications/${a.id}`} className="text-xs font-medium text-[var(--bo-primary)] hover:underline">Review</Link>
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
