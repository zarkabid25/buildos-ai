"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CommissionsSubNav } from "@/components/platform/commissions-subnav";
import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useMarketplaceSuppliers } from "@/lib/use-marketplace";
import { useCommissionLedger, useRaiseDispute } from "@/lib/use-commissions";

const KIND_CLASSES: Record<string, string> = {
  accrual: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  reversal: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
  adjustment: "bg-amber-50 text-[var(--bo-warning)]",
};

export default function PlatformCommissionLedgerPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const isReadOnly = admin?.role === "support";

  const [supplierId, setSupplierId] = useState("");
  const [disputingId, setDisputingId] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  const { data: suppliersData } = useMarketplaceSuppliers({ verification_status: "verified" });
  const { data: entries, isLoading: ledgerLoading, isError, error, refetch } = useCommissionLedger({ marketplace_supplier_id: supplierId || undefined });
  const raiseDispute = useRaiseDispute();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleRaiseDispute() {
    if (!disputingId || !reason) return;
    try {
      await raiseDispute.mutateAsync({ ledger_entry_id: disputingId, reason });
      setDisputingId(null);
      setReason("");
      toast("Dispute raised. Review it from the Disputes tab.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Commissions">
      <div className="space-y-5">
        <CommissionsSubNav />

        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Commission Ledger</h1>
              <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">Every accrual, reversal and adjustment -- append-only, nothing here is ever edited in place.</p>
            </div>
            <select
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              className="h-10 w-64 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
            >
              <option value="">All suppliers</option>
              {suppliersData?.suppliers.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {!ledgerLoading && entries && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Supplier</th>
                  <th className="px-4 py-3">Kind</th>
                  <th className="px-4 py-3">Base amount</th>
                  <th className="px-4 py-3">Commission</th>
                  <th className="px-4 py-3">Invoiced</th>
                  <th className="px-4 py-3">Date</th>
                  {!isReadOnly && <th className="px-4 py-3"></th>}
                </tr>
              </thead>
              <tbody>
                {entries.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-[var(--bo-text-muted)]">No ledger entries yet.</td></tr>
                )}
                {entries.map((e) => (
                  <tr key={e.id} className="h-14 border-t border-[var(--bo-divider)]">
                    <td className="px-4 py-3 font-medium text-[var(--bo-text)]">{e.marketplace_supplier_name ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${KIND_CLASSES[e.kind]}`}>{e.kind}</span>
                    </td>
                    <td className="bo-tabular px-4 py-3 text-[var(--bo-text-muted)]">{e.base_amount}</td>
                    <td className="bo-tabular px-4 py-3 text-[var(--bo-text)]">{e.commission_amount}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{e.invoiced ? "Yes" : "No"}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{new Date(e.created_at).toLocaleDateString()}</td>
                    {!isReadOnly && (
                      <td className="px-4 py-3 text-right">
                        {e.kind === "accrual" && (
                          <button onClick={() => setDisputingId(e.id)} className="text-xs font-medium text-[var(--bo-primary)] hover:underline">
                            Dispute
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {disputingId && (
          <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
            <h2 className="text-sm font-semibold text-[var(--bo-text)]">Raise a dispute</h2>
            <div className="mt-3 flex flex-wrap items-end gap-3">
              <div className="flex-1">
                <Label htmlFor="reason">Reason</Label>
                <Input id="reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this entry being disputed?" />
              </div>
              <button onClick={handleRaiseDispute} disabled={!reason || raiseDispute.isPending} className="h-10 rounded-md bg-[var(--bo-primary)] px-4 text-sm font-medium text-[var(--bo-on-primary)] hover:bg-[var(--bo-primary-hover)] disabled:opacity-50">
                {raiseDispute.isPending ? "Submitting..." : "Submit dispute"}
              </button>
              <button onClick={() => { setDisputingId(null); setReason(""); }} className="h-10 rounded-md border border-[var(--bo-border)] px-4 text-sm font-medium text-[var(--bo-text-secondary)]">
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </PlatformShell>
  );
}
