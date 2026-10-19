"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { SupplierShell } from "@/components/supplier-shell";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSupplierRfqInbox } from "@/lib/use-supplier-portal";

const STATUS_CLASSES: Record<string, string> = {
  invited: "bg-blue-50 text-blue-700",
  quoted: "bg-green-50 text-green-700",
  declined: "bg-gray-100 text-gray-500",
};

export default function SupplierRfqInboxPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const [status, setStatus] = useState("");
  const { data, isLoading, isError, error, refetch } = useSupplierRfqInbox(status || undefined);

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  return (
    <SupplierShell breadcrumb="RFQs">
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">RFQ Inbox</h1>
            <p className="mt-1 text-sm text-gray-500">Requests for quotation from companies you're connected with.</p>
          </div>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="h-11 rounded-lg border border-gray-300 bg-white px-3 text-sm">
            <option value="">All</option>
            <option value="invited">Needs response</option>
            <option value="quoted">Quoted</option>
            <option value="declined">Declined</option>
          </select>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {isLoading && <TableSkeleton rows={4} />}
        {data && data.length === 0 && <EmptyState title="No RFQ invitations" hint="Invitations from connected companies will show up here." />}
        {data && data.length > 0 && (
          <div className="space-y-2">
            {data.map((r) => (
              <Link
                key={r.invitation_id}
                href={`/supplier-portal/rfqs/${r.rfq_id}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-gray-200 bg-white p-4 hover:border-blue-300 hover:shadow-sm"
              >
                <div>
                  <p className="font-medium text-gray-900">{r.title}</p>
                  <p className="text-sm text-gray-500">{r.rfq_number} &middot; {r.company_name}</p>
                </div>
                <div className="flex items-center gap-3">
                  {r.response_due && <span className="text-xs text-gray-400">Due {r.response_due}</span>}
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_CLASSES[r.status] ?? ""}`}>{r.status}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </SupplierShell>
  );
}
