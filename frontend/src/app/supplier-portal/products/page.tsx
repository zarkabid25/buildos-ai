"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { SupplierShell } from "@/components/supplier-shell";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSupplierProducts } from "@/lib/use-supplier-portal";

export default function SupplierProductsPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const { data, isLoading, isError, error, refetch } = useSupplierProducts({ search });

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  return (
    <SupplierShell breadcrumb="Products">
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Product Catalog</h1>
            <p className="mt-1 text-sm text-gray-500">What companies see when they browse your listing in the marketplace.</p>
          </div>
          <Link href="/supplier-portal/products/new">
            <Button className="h-11">Add product</Button>
          </Link>
        </div>

        <div className="flex h-11 w-full max-w-sm items-center gap-2 rounded-lg border border-gray-300 bg-white px-3">
          <Search className="h-4 w-4 text-gray-400" />
          <input placeholder="Search products..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-transparent text-sm focus:outline-none" />
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {isLoading && <TableSkeleton rows={4} />}
        {data && data.length === 0 && <EmptyState title="No products yet" hint="Add your first product to appear in company searches." />}
        {data && data.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Price</th>
                  <th className="px-4 py-3">MOQ</th>
                  <th className="px-4 py-3">Lead time</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.map((p) => (
                  <tr key={p.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link href={`/supplier-portal/products/${p.id}`} className="font-medium text-blue-600 hover:underline">{p.name}</Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{p.category ?? "—"}</td>
                    <td className="bo-tabular px-4 py-3 text-gray-900">{p.price}</td>
                    <td className="px-4 py-3 text-gray-600">{p.minimum_order_quantity} {p.unit}</td>
                    <td className="px-4 py-3 text-gray-600">{p.lead_time_days != null ? `${p.lead_time_days}d` : "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${p.is_active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                        {p.is_active ? "Active" : "Inactive"}
                      </span>
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
