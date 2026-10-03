"use client";

import { Card } from "@/components/ui/card";
import { useSupplierPerformance, useSupplierTransactions } from "@/lib/use-suppliers";
import { formatCurrency } from "@/lib/utils";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="text-lg font-semibold text-ink">{value}</div>
    </div>
  );
}

export function SupplierActivityPanel({ supplierId, supplierName }: { supplierId: string; supplierName: string }) {
  const { data: perf } = useSupplierPerformance(supplierId);
  const { data: transactions, isLoading } = useSupplierTransactions(supplierId);

  return (
    <Card className="space-y-4">
      <h2 className="text-base font-semibold text-ink">{supplierName}: orders and performance</h2>

      {perf && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Purchase orders" value={`${perf.po_count} (${perf.committed_po_count} approved)`} />
            <Stat label="Committed" value={formatCurrency(perf.committed_amount)} />
            <Stat
              label="Received"
              value={perf.fulfilment_percent !== null ? `${perf.fulfilment_percent}%` : "—"}
            />
            <Stat
              label="Avg lead time"
              value={perf.average_lead_time_days !== null ? `${perf.average_lead_time_days} days` : "—"}
            />
          </div>
          <p className="text-xs text-muted">{perf.note}</p>
        </>
      )}

      {isLoading && <p className="text-sm text-muted">Loading orders...</p>}
      {transactions && transactions.length === 0 && (
        <p className="text-sm text-muted">No purchase orders with this supplier yet.</p>
      )}
      {transactions && transactions.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-2 py-2">PO</th>
                <th className="px-2 py-2">Date</th>
                <th className="px-2 py-2">Project</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Ordered</th>
                <th className="px-2 py-2">Received</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.purchase_order_id} className="border-b border-border last:border-0">
                  <td className="px-2 py-2 font-medium text-ink">{t.po_number}</td>
                  <td className="px-2 py-2 text-muted">{t.created_at.slice(0, 10)}</td>
                  <td className="px-2 py-2 text-muted">{t.project_name ?? "—"}</td>
                  <td className="px-2 py-2 capitalize">{t.status.replace(/_/g, " ")}</td>
                  <td className="px-2 py-2">{formatCurrency(t.ordered_amount)}</td>
                  <td className="px-2 py-2">
                    {formatCurrency(t.received_amount)}
                    {t.receipt_count > 0 && (
                      <span className="ml-1 text-xs text-muted">
                        ({t.receipt_count} receipt{t.receipt_count === 1 ? "" : "s"})
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
