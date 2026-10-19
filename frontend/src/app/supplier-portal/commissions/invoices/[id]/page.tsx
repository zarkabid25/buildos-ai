"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

import { SupplierShell } from "@/components/supplier-shell";
import { Card } from "@/components/ui/card";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSupplierCommissionInvoice } from "@/lib/use-supplier-portal";

export default function SupplierCommissionInvoiceDetailPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { data: invoice, isLoading, isError, error, refetch } = useSupplierCommissionInvoice(params.id);

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  return (
    <SupplierShell breadcrumb="Commissions">
      <div className="max-w-xl space-y-5">
        {isLoading && <Skeleton className="h-64 w-full" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {invoice && (
          <>
            <Card className="space-y-2">
              <div className="flex items-center justify-between">
                <h1 className="text-lg font-semibold text-gray-900">{invoice.invoice_number}</h1>
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium capitalize text-gray-700">{invoice.status.replace("_", " ")}</span>
              </div>
              <p className="text-sm text-gray-500">{invoice.period_start} &ndash; {invoice.period_end} &middot; due {invoice.due_date}</p>
              <table className="w-full text-sm">
                <tbody>
                  {invoice.items.map((item) => (
                    <tr key={item.id} className="border-b border-gray-100">
                      <td className="py-2 text-gray-900">{item.description}</td>
                      <td className="py-2 text-right font-medium text-gray-900">{item.amount}</td>
                    </tr>
                  ))}
                  <tr>
                    <td className="py-2 text-right font-semibold text-gray-900">Total</td>
                    <td className="py-2 text-right font-semibold text-gray-900">{invoice.total_amount} {invoice.currency}</td>
                  </tr>
                </tbody>
              </table>
            </Card>

            <Card className="space-y-2">
              <h2 className="text-sm font-semibold text-gray-900">Settlements</h2>
              {invoice.payments.length === 0 && <p className="text-sm text-gray-500">No payments recorded yet.</p>}
              <ul className="space-y-1">
                {invoice.payments.map((p) => (
                  <li key={p.id} className="flex justify-between text-sm">
                    <span className="text-gray-900">{p.amount} &middot; {p.receipt_reference ?? "no reference"}</span>
                    <span className="text-gray-500">{p.paid_on}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </>
        )}
      </div>
    </SupplierShell>
  );
}
