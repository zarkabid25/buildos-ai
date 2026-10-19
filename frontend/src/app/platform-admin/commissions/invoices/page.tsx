"use client";

import { Fragment, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CommissionsSubNav } from "@/components/platform/commissions-subnav";
import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useMarketplaceSuppliers } from "@/lib/use-marketplace";
import { useCommissionInvoices, useGenerateCommissionInvoice, useRecordCommissionPayment } from "@/lib/use-commissions";

const STATUS_CLASSES: Record<string, string> = {
  draft: "bg-gray-100 text-[var(--bo-text-muted)]",
  pending: "bg-amber-50 text-[var(--bo-warning)]",
  partially_paid: "bg-amber-50 text-[var(--bo-warning)]",
  paid: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  void: "bg-gray-100 text-[var(--bo-text-muted)]",
};

function RecordPaymentRow({ invoiceId, onDone }: { invoiceId: string; onDone: () => void }) {
  const { toast } = useFeedback();
  const [amount, setAmount] = useState("");
  const [paidOn, setPaidOn] = useState(new Date().toISOString().slice(0, 10));
  const [reference, setReference] = useState("");
  const recordPayment = useRecordCommissionPayment(invoiceId);

  async function handleSubmit() {
    try {
      await recordPayment.mutateAsync({ amount, paid_on: paidOn, receipt_reference: reference || undefined });
      toast("Payment recorded.", "success");
      onDone();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <div className="flex flex-wrap items-end gap-2">
      <Input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Amount" className="w-28" />
      <Input type="date" value={paidOn} onChange={(e) => setPaidOn(e.target.value)} className="w-36" />
      <Input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Receipt ref." className="w-32" />
      <Button onClick={handleSubmit} disabled={!amount || recordPayment.isPending}>
        {recordPayment.isPending ? "Recording..." : "Record payment"}
      </Button>
    </div>
  );
}

export default function PlatformCommissionInvoicesPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const isReadOnly = admin?.role === "support";

  const [supplierId, setSupplierId] = useState("");
  const [periodStart, setPeriodStart] = useState("2026-01-01");
  const [periodEnd, setPeriodEnd] = useState("2026-12-31");
  const [dueDate, setDueDate] = useState("2027-01-15");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [payingId, setPayingId] = useState<string | null>(null);

  const { data: suppliersData } = useMarketplaceSuppliers({ verification_status: "verified" });
  const { data: invoices, isLoading: invoicesLoading, isError, error, refetch } = useCommissionInvoices({ marketplace_supplier_id: supplierId || undefined });
  const generateInvoice = useGenerateCommissionInvoice();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleGenerate() {
    if (!supplierId) return;
    try {
      await generateInvoice.mutateAsync({ marketplace_supplier_id: supplierId, period_start: periodStart, period_end: periodEnd, due_date: dueDate });
      toast("Commission invoice generated.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Commissions">
      <div className="space-y-5">
        <CommissionsSubNav />

        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Commission Invoices</h1>
          <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">Separate numbering and table from SaaS subscription invoices.</p>

          {!isReadOnly && (
            <div className="mt-4 grid gap-3 border-t border-[var(--bo-divider)] pt-4 sm:grid-cols-5">
              <select value={supplierId} onChange={(e) => setSupplierId(e.target.value)} className="h-10 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]">
                <option value="">Select supplier to invoice...</option>
                {suppliersData?.suppliers.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <div>
                <Label htmlFor="period-start">Period start</Label>
                <Input id="period-start" type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="period-end">Period end</Label>
                <Input id="period-end" type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="due-date">Due date</Label>
                <Input id="due-date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </div>
              <div className="flex items-end">
                <Button onClick={handleGenerate} disabled={!supplierId || generateInvoice.isPending} className="w-full">
                  {generateInvoice.isPending ? "Generating..." : "Generate invoice"}
                </Button>
              </div>
            </div>
          )}
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {!invoicesLoading && invoices && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Invoice</th>
                  <th className="px-4 py-3">Supplier</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">Outstanding</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {invoices.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-[var(--bo-text-muted)]">No commission invoices yet.</td></tr>
                )}
                {invoices.map((inv) => (
                  <Fragment key={inv.id}>
                    <tr className="h-14 border-t border-[var(--bo-divider)]">
                      <td className="px-4 py-3 font-medium text-[var(--bo-text)]">{inv.invoice_number}</td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{inv.marketplace_supplier_name ?? "—"}</td>
                      <td className="bo-tabular px-4 py-3 text-[var(--bo-text)]">{inv.total_amount} {inv.currency}</td>
                      <td className="bo-tabular px-4 py-3 text-[var(--bo-text-muted)]">{inv.outstanding}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[inv.status]}`}>{inv.status.replace("_", " ")}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => setExpandedId(expandedId === inv.id ? null : inv.id)} className="text-xs font-medium text-[var(--bo-primary)] hover:underline">
                          {expandedId === inv.id ? "Hide" : "Details"}
                        </button>
                      </td>
                    </tr>
                    {expandedId === inv.id && (
                      <tr className="border-t border-[var(--bo-divider)] bg-[var(--bo-canvas)]">
                        <td colSpan={6} className="px-4 py-4">
                          <div className="grid gap-4 sm:grid-cols-2">
                            <div>
                              <h3 className="text-xs font-medium text-[var(--bo-text-muted)]">Line items</h3>
                              <ul className="mt-2 space-y-1 text-sm">
                                {inv.items.map((item) => (
                                  <li key={item.id} className="flex justify-between text-[var(--bo-text)]">
                                    <span>{item.description}</span>
                                    <span className="bo-tabular">{item.amount}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <h3 className="text-xs font-medium text-[var(--bo-text-muted)]">Payment history</h3>
                              {inv.payments.length === 0 && <p className="mt-2 text-sm text-[var(--bo-text-muted)]">No payments recorded yet.</p>}
                              <ul className="mt-2 space-y-1">
                                {inv.payments.map((p) => (
                                  <li key={p.id} className="flex justify-between text-sm text-[var(--bo-text)]">
                                    <span>{p.amount} &middot; {p.receipt_reference ?? "no reference"}</span>
                                    <span className="text-[var(--bo-text-muted)]">{p.paid_on}</span>
                                  </li>
                                ))}
                              </ul>
                              {!isReadOnly && inv.status !== "paid" && inv.status !== "void" && (
                                <div className="mt-3 border-t border-[var(--bo-divider)] pt-3">
                                  {payingId === inv.id ? (
                                    <RecordPaymentRow invoiceId={inv.id} onDone={() => setPayingId(null)} />
                                  ) : (
                                    <button onClick={() => setPayingId(inv.id)} className="text-xs font-medium text-[var(--bo-primary)] hover:underline">
                                      + Record a payment
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </PlatformShell>
  );
}
