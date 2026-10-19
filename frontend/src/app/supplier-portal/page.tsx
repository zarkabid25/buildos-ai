"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ClipboardList, DollarSign, FileText, Package, ShoppingCart, Truck } from "lucide-react";

import { SupplierShell } from "@/components/supplier-shell";
import { Card } from "@/components/ui/card";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSupplierDashboard } from "@/lib/use-supplier-portal";

function MetricTile({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <Card className="flex items-center gap-4">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">{icon}</div>
      <div>
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </Card>
  );
}

export default function SupplierDashboardPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const { data, isLoading, isError, error, refetch } = useSupplierDashboard();

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  return (
    <SupplierShell breadcrumb="Dashboard">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">What needs your attention right now.</p>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {isLoading && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
          </div>
        )}
        {data && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <MetricTile icon={<ClipboardList className="h-5 w-5" />} label="New RFQ invitations" value={data.new_invitations} />
            <MetricTile icon={<FileText className="h-5 w-5" />} label="Pending quotations" value={data.pending_quotations} />
            <MetricTile icon={<FileText className="h-5 w-5" />} label="Submitted quotations" value={data.submitted_quotations} />
            <MetricTile icon={<ShoppingCart className="h-5 w-5" />} label="Active linked orders" value={data.active_linked_orders} />
            <MetricTile icon={<Truck className="h-5 w-5" />} label="Pending delivery updates" value={data.pending_delivery_updates} />
            <MetricTile icon={<DollarSign className="h-5 w-5" />} label="Outstanding commission invoices" value={data.outstanding_commission_invoices} />
          </div>
        )}

        <Card className="flex items-center gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-600">
            <Package className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">Keep your catalog current</p>
            <p className="text-sm text-gray-500">Companies browsing the marketplace only see active, accurately priced products.</p>
          </div>
        </Card>
      </div>
    </SupplierShell>
  );
}
