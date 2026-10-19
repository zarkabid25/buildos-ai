"use client";

import { useEffect, useState } from "react";
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
import { useCancelCommissionAgreement, useCommissionAgreements, useCreateCommissionAgreement } from "@/lib/use-commissions";
import type { CommissionBasis } from "@/lib/commission-types";

const STATUS_CLASSES: Record<string, string> = {
  active: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  superseded: "bg-gray-100 text-[var(--bo-text-muted)]",
  cancelled: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
};

export default function PlatformCommissionAgreementsPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast, confirm } = useFeedback();
  const isReadOnly = admin?.role === "support";

  const [supplierId, setSupplierId] = useState("");
  const [basis, setBasis] = useState<CommissionBasis>("percentage");
  const [rate, setRate] = useState("");
  const [fixedFee, setFixedFee] = useState("");
  const [notes, setNotes] = useState("");

  const { data: suppliersData } = useMarketplaceSuppliers({ verification_status: "verified" });
  const { data: agreements, isLoading: agreementsLoading, isError, error, refetch } = useCommissionAgreements(supplierId || undefined);
  const createAgreement = useCreateCommissionAgreement(supplierId);
  const cancelAgreement = useCancelCommissionAgreement(supplierId);

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleCreate() {
    try {
      await createAgreement.mutateAsync({
        basis,
        rate: basis === "percentage" ? rate : undefined,
        fixed_fee_amount: basis === "fixed_fee" ? fixedFee : undefined,
        notes: notes || undefined,
      });
      setRate("");
      setFixedFee("");
      setNotes("");
      toast("Commission agreement created.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleCancel(agreementId: string) {
    const ok = await confirm({ title: "Cancel this agreement?", body: "This supplier will have no active commission agreement until a new one is created.", confirmLabel: "Cancel agreement", danger: true });
    if (!ok) return;
    try {
      await cancelAgreement.mutateAsync(agreementId);
      toast("Agreement cancelled.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Commissions">
      <div className="space-y-5">
        <CommissionsSubNav />

        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Supplier Commission Agreements</h1>
          <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">One active agreement per supplier -- a change always supersedes, never edits.</p>

          <div className="mt-4">
            <Label htmlFor="supplier-select">Supplier</Label>
            <select
              id="supplier-select"
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              className="h-10 w-full max-w-sm rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
            >
              <option value="">Select a verified supplier...</option>
              {suppliersData?.suppliers.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          {supplierId && !isReadOnly && (
            <form onSubmit={(e) => { e.preventDefault(); handleCreate(); }} className="mt-4 grid gap-3 border-t border-[var(--bo-divider)] pt-4 sm:grid-cols-4">
              <div>
                <Label htmlFor="basis">Basis</Label>
                <select id="basis" value={basis} onChange={(e) => setBasis(e.target.value as CommissionBasis)} className="h-10 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]">
                  <option value="percentage">Percentage</option>
                  <option value="fixed_fee">Fixed fee</option>
                </select>
              </div>
              {basis === "percentage" ? (
                <div>
                  <Label htmlFor="rate">Rate (e.g. 0.05 = 5%)</Label>
                  <Input id="rate" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="0.0500" />
                </div>
              ) : (
                <div>
                  <Label htmlFor="fixed-fee">Fixed fee amount</Label>
                  <Input id="fixed-fee" value={fixedFee} onChange={(e) => setFixedFee(e.target.value)} placeholder="25.00" />
                </div>
              )}
              <div className="sm:col-span-2">
                <Label htmlFor="notes">Notes</Label>
                <Input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" />
              </div>
              <div className="flex items-end sm:col-span-4">
                <Button type="submit" disabled={createAgreement.isPending}>
                  {createAgreement.isPending ? "Creating..." : "Create agreement"}
                </Button>
              </div>
            </form>
          )}
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {supplierId && !agreementsLoading && agreements && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Version</th>
                  <th className="px-4 py-3">Basis</th>
                  <th className="px-4 py-3">Rate / Fee</th>
                  <th className="px-4 py-3">Effective</th>
                  <th className="px-4 py-3">Status</th>
                  {!isReadOnly && <th className="px-4 py-3"></th>}
                </tr>
              </thead>
              <tbody>
                {agreements.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-[var(--bo-text-muted)]">No agreements yet for this supplier.</td></tr>
                )}
                {agreements.map((a) => (
                  <tr key={a.id} className="h-14 border-t border-[var(--bo-divider)]">
                    <td className="px-4 py-3 font-medium text-[var(--bo-text)]">v{a.version}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)] capitalize">{a.basis.replace("_", " ")}</td>
                    <td className="bo-tabular px-4 py-3 text-[var(--bo-text)]">{a.basis === "percentage" ? `${(Number(a.rate) * 100).toFixed(2)}%` : `$${a.fixed_fee_amount}`}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">
                      {new Date(a.effective_from).toLocaleDateString()} {a.effective_to ? `– ${new Date(a.effective_to).toLocaleDateString()}` : "– ongoing"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[a.status]}`}>{a.status}</span>
                    </td>
                    {!isReadOnly && (
                      <td className="px-4 py-3 text-right">
                        {a.status === "active" && (
                          <button onClick={() => handleCancel(a.id)} className="text-xs font-medium text-[var(--bo-danger)] hover:underline">
                            Cancel
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
      </div>
    </PlatformShell>
  );
}
