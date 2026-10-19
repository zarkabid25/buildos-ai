"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { SupplierShell } from "@/components/supplier-shell";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSupplierQuotationHistory } from "@/lib/use-supplier-portal";

export default function SupplierQuotationHistoryPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const { data, isLoading, isError, error, refetch } = useSupplierQuotationHistory();

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  return (
    <SupplierShell breadcrumb="Quotations">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Quotation History</h1>
          <p className="mt-1 text-sm text-gray-500">Every quotation you've submitted, across every connected company.</p>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {isLoading && <TableSkeleton rows={4} />}
        {data && data.length === 0 && <EmptyState title="No quotations submitted yet" />}
        {data && data.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3">RFQ</th>
                  <th className="px-4 py-3">Company</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">Submitted</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {data.map((q, i) => (
                  <tr key={i} className="border-b border-gray-100 last:border-0">
                    <td className="px-4 py-3 text-gray-900">{q.rfq_number}</td>
                    <td className="px-4 py-3 text-gray-600">{q.company_name}</td>
                    <td className="bo-tabular px-4 py-3 text-gray-900">{q.total}</td>
                    <td className="px-4 py-3 text-gray-500">{new Date(q.submitted_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/supplier-portal/rfqs/${q.rfq_id}`} className="text-xs font-medium text-blue-600 hover:underline">View</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </SupplierShell>
  );
}
