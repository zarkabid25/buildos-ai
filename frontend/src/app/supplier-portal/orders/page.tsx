"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { SupplierShell } from "@/components/supplier-shell";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSupplierOrders } from "@/lib/use-supplier-portal";

const STATUS_CLASSES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-500",
  pending_approval: "bg-amber-50 text-amber-700",
  approved: "bg-blue-50 text-blue-700",
  partially_received: "bg-amber-50 text-amber-700",
  received: "bg-green-50 text-green-700",
  cancelled: "bg-red-50 text-red-700",
};

export default function SupplierOrdersPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const { data, isLoading, isError, error, refetch } = useSupplierOrders();

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  return (
    <SupplierShell breadcrumb="Orders">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Orders</h1>
          <p className="mt-1 text-sm text-gray-500">Purchase orders linked to your marketplace-sourced quotations.</p>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {isLoading && <TableSkeleton rows={4} />}
        {data && data.length === 0 && <EmptyState title="No linked orders yet" hint="Orders appear here once a company awards one of your quotations." />}
        {data && data.length > 0 && (
          <div className="space-y-2">
            {data.map((o) => (
              <Link
                key={o.purchase_order_id}
                href={`/supplier-portal/orders/${o.purchase_order_id}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-gray-200 bg-white p-4 hover:border-blue-300 hover:shadow-sm"
              >
                <div>
                  <p className="font-medium text-gray-900">{o.po_number}</p>
                  <p className="text-sm text-gray-500">{o.company_name}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="bo-tabular text-sm text-gray-700">{o.total_amount}</span>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${STATUS_CLASSES[o.status] ?? ""}`}>{o.status.replace("_", " ")}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </SupplierShell>
  );
}
