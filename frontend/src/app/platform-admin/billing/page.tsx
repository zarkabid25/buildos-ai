"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { DollarSign, FileWarning, RefreshCcw, Users2 } from "lucide-react";

import { useFeedback } from "@/components/feedback";
import { MetricCard } from "@/components/platform/metric-card";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useBillingOverview, usePendingPayments, useRejectPayment, useVerifyPayment } from "@/lib/use-platform-billing";

export default function PlatformBillingPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast, confirm } = useFeedback();
  const isReadOnly = admin?.role === "support";

  const { data: overview, isLoading: overviewLoading } = useBillingOverview();
  const { data: pending, isLoading: pendingLoading, isError, error, refetch } = usePendingPayments();
  const verify = useVerifyPayment();
  const reject = useRejectPayment();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleVerify(id: string) {
    const ok = await confirm({ title: "Verify this payment?", body: "This activates the company's subscription immediately.", confirmLabel: "Verify" });
    if (!ok) return;
    try {
      await verify.mutateAsync(id);
      toast("Payment verified, subscription activated.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleReject(id: string) {
    const reason = window.prompt("Reason for rejecting this payment?");
    if (!reason) return;
    try {
      await reject.mutateAsync({ submissionId: id, reason });
      toast("Payment rejected.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Billing">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.025em] text-[var(--bo-text)]">Subscriptions &amp; Billing</h1>
          <p className="mt-1 text-sm text-[var(--bo-text-secondary)]">Revenue, pending payments, and plan management.</p>
        </div>

        {!overviewLoading && overview && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
            <MetricCard icon={<Users2 className="h-4 w-4" />} label="Active + Trialing" value={String(overview.active_subscriptions)} dateRange="Right now" />
            <MetricCard icon={<RefreshCcw className="h-4 w-4" />} label="In Grace Period" value={String(overview.in_grace_period)} dateRange="Right now" />
            <MetricCard icon={<FileWarning className="h-4 w-4" />} label="Pending Payments" value={String(overview.pending_payments)} dateRange="Right now" />
            <MetricCard icon={<DollarSign className="h-4 w-4" />} label="Revenue Collected" value={`$${overview.total_revenue_collected}`} dateRange="All time" />
          </div>
        )}

        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Pending payments</h2>
          <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">Manual bank-transfer submissions awaiting verification.</p>

          {isError && (
            <div className="mt-4">
              <ErrorState error={error} onRetry={() => refetch()} />
            </div>
          )}
          {!pendingLoading && pending && pending.length === 0 && <p className="mt-4 text-sm text-[var(--bo-text-muted)]">Nothing pending.</p>}
          {pending && pending.length > 0 && (
            <div className="mt-4 overflow-x-auto rounded-lg border border-[var(--bo-divider)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                  <tr>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Reference</th>
                    <th className="px-4 py-3">Submitted</th>
                    {!isReadOnly && <th className="px-4 py-3"></th>}
                  </tr>
                </thead>
                <tbody>
                  {pending.map((p) => (
                    <tr key={p.id} className="h-14 border-t border-[var(--bo-divider)]">
                      <td className="bo-tabular px-4 py-3 font-medium text-[var(--bo-text)]">{p.amount}</td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{p.reference ?? "—"}</td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{new Date(p.created_at).toLocaleString()}</td>
                      {!isReadOnly && (
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            <button onClick={() => handleVerify(p.id)} className="h-9 rounded-md bg-[var(--bo-primary)] px-3 text-sm font-medium text-[var(--bo-on-primary)] hover:bg-[var(--bo-primary-hover)]">
                              Verify
                            </button>
                            <button onClick={() => handleReject(p.id)} className="h-9 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm font-medium text-[var(--bo-danger)] hover:bg-[var(--bo-surface-hover)]">
                              Reject
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </PlatformShell>
  );
}
