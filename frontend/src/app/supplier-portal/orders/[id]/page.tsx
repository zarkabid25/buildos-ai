"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { SupplierShell } from "@/components/supplier-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/supplier-api";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSubmitDeliveryUpdate, useSupplierDeliveryUpdates, useSupplierOrder } from "@/lib/use-supplier-portal";

export default function SupplierOrderDetailPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useFeedback();
  const { data: order, isLoading, isError, error, refetch } = useSupplierOrder(params.id);
  const updatesQuery = useSupplierDeliveryUpdates(params.id);
  const submitUpdate = useSubmitDeliveryUpdate(params.id);

  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  async function handleSubmit() {
    if (!reference) return;
    try {
      const result = await submitUpdate.mutateAsync({ external_reference: reference, note: note || undefined });
      setReference("");
      setNote("");
      toast(result.already_recorded ? "That delivery reference was already recorded." : "Delivery update recorded.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <SupplierShell breadcrumb="Orders">
      <div className="max-w-2xl space-y-5">
        {isLoading && <Skeleton className="h-64 w-full" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {order && (
          <>
            <Card className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h1 className="text-lg font-semibold text-gray-900">{order.po_number}</h1>
                <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium capitalize text-blue-700">{order.status.replace("_", " ")}</span>
              </div>
              <p className="text-sm text-gray-500">{order.company_name}</p>
              <p className="text-sm text-gray-700">Total {order.total_amount} &middot; Paid {order.amount_paid}</p>
            </Card>

            <Card className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-900">Order items</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
                    <th className="py-2">Material</th>
                    <th className="py-2">Qty</th>
                    <th className="py-2">Received</th>
                    <th className="py-2">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items.map((item) => (
                    <tr key={item.id} className="border-b border-gray-100 last:border-0">
                      <td className="py-2 text-gray-900">{item.material_name}</td>
                      <td className="py-2 text-gray-600">{item.quantity}</td>
                      <td className="py-2 text-gray-600">{item.quantity_received}</td>
                      <td className="py-2 text-gray-900">{item.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            <Card className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-900">Delivery updates</h2>
              <p className="text-xs text-gray-400">Informational only -- these never post stock or change ERP inventory.</p>
              {updatesQuery.isLoading && <Skeleton className="h-16 w-full" />}
              {updatesQuery.data && updatesQuery.data.length === 0 && <EmptyState title="No delivery updates yet" />}
              <ul className="space-y-2">
                {updatesQuery.data?.map((u) => (
                  <li key={u.id} className="rounded-md border border-gray-200 px-3 py-2 text-sm">
                    <p className="font-medium text-gray-900">{u.external_reference}</p>
                    {u.note && <p className="text-gray-600">{u.note}</p>}
                    <p className="text-xs text-gray-400">{new Date(u.created_at).toLocaleString()}</p>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap items-end gap-2 border-t border-gray-100 pt-3">
                <div>
                  <Label htmlFor="ref">Reference</Label>
                  <Input id="ref" value={reference} onChange={(e) => setReference(e.target.value)} placeholder="SHIP-001" />
                </div>
                <div className="flex-1">
                  <Label htmlFor="note">Note (optional)</Label>
                  <Input id="note" value={note} onChange={(e) => setNote(e.target.value)} />
                </div>
                <Button onClick={handleSubmit} disabled={!reference || submitUpdate.isPending}>
                  {submitUpdate.isPending ? "Submitting..." : "Report update"}
                </Button>
              </div>
            </Card>
          </>
        )}
      </div>
    </SupplierShell>
  );
}
