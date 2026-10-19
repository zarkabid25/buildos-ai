"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { UserRole } from "@/lib/auth-types";
import { fetchPaymentProofBlob, useInvoice, useSubmitPayment } from "@/lib/use-billing";

const CAN_MANAGE: UserRole[] = ["super_admin", "company_admin"];

const PAYMENT_STATUS_CLASSES: Record<string, string> = {
  pending: "bg-amber-50 text-warning",
  verified: "bg-green-50 text-success",
  rejected: "bg-red-50 text-danger",
};

export default function InvoiceDetailPage() {
  const { user, isLoading, accessToken } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useFeedback();
  const canManage = !!user && CAN_MANAGE.includes(user.role);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");

  const { data: invoice, isLoading: invoiceLoading, isError, error, refetch } = useInvoice(params.id);
  const submitPayment = useSubmitPayment(params.id);

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  useEffect(() => {
    if (invoice && !amount) setAmount(invoice.total_amount);
  }, [invoice, amount]);

  if (isLoading || !user) return null;

  async function handleSubmit() {
    const file = fileInputRef.current?.files?.[0];
    if (!file || !amount) return;
    try {
      await submitPayment.mutateAsync({ amount, reference: reference || undefined, file });
      setReference("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      toast("Payment submitted. Platform staff will verify it shortly.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Submission failed.", "error");
    }
  }

  async function handleDownloadProof(submissionId: string, filename: string) {
    if (!accessToken) return;
    try {
      const blob = await fetchPaymentProofBlob(submissionId, accessToken);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't download.", "error");
    }
  }

  return (
    <AppShell>
      <div className="max-w-2xl space-y-4">
        {invoiceLoading && (
          <Card>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="mt-4 h-4 w-full" />
          </Card>
        )}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {invoice && (
          <>
            <Card className="space-y-2">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h1 className="text-lg font-semibold text-ink">{invoice.invoice_number}</h1>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium capitalize text-ink">{invoice.status}</span>
              </div>
              <p className="text-sm text-muted">
                Billing period {invoice.billing_period_start} &ndash; {invoice.billing_period_end} &middot; due {invoice.due_date}
              </p>
              <table className="w-full text-sm">
                <tbody>
                  {invoice.items.map((item) => (
                    <tr key={item.id} className="border-b border-border">
                      <td className="py-2 text-ink">{item.description}</td>
                      <td className="py-2 text-right text-muted">
                        {item.quantity} &times; {item.unit_price}
                      </td>
                      <td className="py-2 text-right font-medium text-ink">{item.amount}</td>
                    </tr>
                  ))}
                  {Number(invoice.discount_amount) > 0 && (
                    <tr>
                      <td colSpan={2} className="py-1 text-right text-muted">Discount</td>
                      <td className="py-1 text-right text-muted">-{invoice.discount_amount}</td>
                    </tr>
                  )}
                  {Number(invoice.tax_amount) > 0 && (
                    <tr>
                      <td colSpan={2} className="py-1 text-right text-muted">Tax</td>
                      <td className="py-1 text-right text-muted">{invoice.tax_amount}</td>
                    </tr>
                  )}
                  <tr>
                    <td colSpan={2} className="py-2 text-right font-semibold text-ink">Total</td>
                    <td className="py-2 text-right font-semibold text-ink">{invoice.total_amount} {invoice.currency}</td>
                  </tr>
                </tbody>
              </table>
            </Card>

            <Card className="space-y-3">
              <h2 className="text-sm font-semibold text-ink">Payments</h2>
              {invoice.payments.length === 0 && <p className="text-sm text-muted">No payment submitted yet.</p>}
              <ul className="space-y-2">
                {invoice.payments.map((p) => (
                  <li key={p.id} className="flex items-center justify-between rounded-md border border-border p-3 text-sm">
                    <div>
                      <p className="font-medium text-ink">{p.amount} &middot; {p.reference ?? "no reference"}</p>
                      {p.status === "rejected" && p.rejection_reason && <p className="text-xs text-danger">Rejected: {p.rejection_reason}</p>}
                      {p.status === "verified" && p.verified_by_staff_name && <p className="text-xs text-muted">Verified by {p.verified_by_staff_name}</p>}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${PAYMENT_STATUS_CLASSES[p.status]}`}>{p.status}</span>
                      <button onClick={() => handleDownloadProof(p.id, p.proof_filename)} className="text-xs font-medium text-primary hover:underline">
                        Proof
                      </button>
                    </div>
                  </li>
                ))}
              </ul>

              {canManage && invoice.status === "pending" && (
                <div className="space-y-2 border-t border-border pt-3">
                  <h3 className="text-sm font-medium text-ink">Submit a bank transfer payment</h3>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                    <div>
                      <Label htmlFor="amount">Amount</Label>
                      <Input id="amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
                    </div>
                    <div>
                      <Label htmlFor="reference">Reference (optional)</Label>
                      <Input id="reference" value={reference} onChange={(e) => setReference(e.target.value)} />
                    </div>
                    <div>
                      <Label htmlFor="proof">Proof of transfer</Label>
                      <input ref={fileInputRef} id="proof" type="file" className="block text-sm" />
                    </div>
                  </div>
                  <Button onClick={handleSubmit} disabled={submitPayment.isPending || !amount}>
                    {submitPayment.isPending ? "Submitting..." : "Submit payment"}
                  </Button>
                </div>
              )}
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}
