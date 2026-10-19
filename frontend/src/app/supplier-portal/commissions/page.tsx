"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { SupplierShell } from "@/components/supplier-shell";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import {
  useSupplierCommissionAgreements,
  useSupplierCommissionDisputes,
  useSupplierCommissionInvoices,
  useSupplierCommissionLedger,
} from "@/lib/use-supplier-portal";

const INVOICE_STATUS_CLASSES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-500",
  pending: "bg-amber-50 text-amber-700",
  partially_paid: "bg-amber-50 text-amber-700",
  paid: "bg-green-50 text-green-700",
  void: "bg-gray-100 text-gray-500",
};

export default function SupplierCommissionsPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const agreementsQuery = useSupplierCommissionAgreements();
  const ledgerQuery = useSupplierCommissionLedger();
  const invoicesQuery = useSupplierCommissionInvoices();
  const disputesQuery = useSupplierCommissionDisputes();

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  const outstanding = invoicesQuery.data?.reduce((sum, inv) => sum + Number(inv.outstanding), 0) ?? 0;

  return (
    <SupplierShell breadcrumb="Commissions">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Commission Statement</h1>
          <p className="mt-1 text-sm text-gray-500">What you've earned, been invoiced, and currently owe -- read-only.</p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card>
            <p className="text-sm text-gray-500">Active agreement</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {agreementsQuery.data?.find((a) => a.status === "active")
                ? agreementsQuery.data.find((a) => a.status === "active")!.basis === "percentage"
                  ? `${(Number(agreementsQuery.data.find((a) => a.status === "active")!.rate) * 100).toFixed(2)}%`
                  : `$${agreementsQuery.data.find((a) => a.status === "active")!.fixed_fee_amount} flat`
                : "None"}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Outstanding balance</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">${outstanding.toFixed(2)}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Open disputes</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">{disputesQuery.data?.filter((d) => d.status === "open").length ?? 0}</p>
          </Card>
        </div>

        <Card className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-900">Invoices</h2>
          {invoicesQuery.isLoading && <TableSkeleton rows={2} />}
          {invoicesQuery.isError && <ErrorState error={invoicesQuery.error} onRetry={() => invoicesQuery.refetch()} />}
          {invoicesQuery.data && invoicesQuery.data.length === 0 && <EmptyState title="No commission invoices yet" />}
          <ul className="space-y-2">
            {invoicesQuery.data?.map((inv) => (
              <li key={inv.id}>
                <Link href={`/supplier-portal/commissions/invoices/${inv.id}`} className="flex items-center justify-between rounded-md border border-gray-200 px-3 py-2 text-sm hover:border-blue-300">
                  <span className="font-medium text-gray-900">{inv.invoice_number}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-700">{inv.total_amount} {inv.currency}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${INVOICE_STATUS_CLASSES[inv.status]}`}>{inv.status.replace("_", " ")}</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-900">Ledger</h2>
          {ledgerQuery.isLoading && <TableSkeleton rows={2} />}
          {ledgerQuery.data && ledgerQuery.data.length === 0 && <EmptyState title="No commission activity yet" />}
          <ul className="space-y-1">
            {ledgerQuery.data?.map((e) => (
              <li key={e.id} className="flex items-center justify-between text-sm">
                <span className="capitalize text-gray-700">{e.kind}</span>
                <span className={Number(e.commission_amount) < 0 ? "text-red-600" : "text-gray-900"}>{e.commission_amount}</span>
              </li>
            ))}
          </ul>
        </Card>

        {disputesQuery.data && disputesQuery.data.length > 0 && (
          <Card className="space-y-3">
            <h2 className="text-sm font-semibold text-gray-900">Disputes</h2>
            <ul className="space-y-2">
              {disputesQuery.data.map((d) => (
                <li key={d.id} className="rounded-md border border-gray-200 px-3 py-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-900">{d.reason}</span>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium capitalize text-gray-700">{d.status}</span>
                  </div>
                  {d.resolution_notes && <p className="mt-1 text-xs text-gray-500">{d.resolution_notes}</p>}
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </SupplierShell>
  );
}
