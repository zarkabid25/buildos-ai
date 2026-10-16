"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { usePlatformCompanies } from "@/lib/use-platform";
import { useAssistInviteSuppliers, useCompanyRfqDetail, useCompanyRfqs, useSupplierMatch } from "@/lib/use-marketplace";

export default function MarketplaceMatchPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const [companyId, setCompanyId] = useState("");
  const [rfqId, setRfqId] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [area, setArea] = useState("");

  const { data: companiesData } = usePlatformCompanies("");
  const { data: rfqs } = useCompanyRfqs(companyId);
  const { data: rfqDetail } = useCompanyRfqDetail(companyId, rfqId);
  const matchQuery = useSupplierMatch(companyId, materialId, area || undefined);
  const invite = useAssistInviteSuppliers(companyId, rfqId);

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  useEffect(() => {
    setRfqId("");
    setMaterialId("");
  }, [companyId]);

  useEffect(() => {
    setMaterialId("");
  }, [rfqId]);

  if (isLoading || !admin) return null;

  const openRfqs = (rfqs ?? []).filter((r) => r.status === "open");

  async function handleInvite(marketplaceSupplierId: string) {
    if (!rfqId) return;
    try {
      await invite.mutateAsync([marketplaceSupplierId]);
      toast("Supplier invited to this RFQ.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Supplier Matching">
      <div className="space-y-5">
        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Supplier Matching</h1>
          <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">
            Find eligible marketplace suppliers for a company's open RFQ, using real catalog data only -- never an invented score.
          </p>

          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--bo-text-muted)]">Company</label>
              <select
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
                className="h-10 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
              >
                <option value="">Select a company</option>
                {companiesData?.companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--bo-text-muted)]">Open RFQ</label>
              <select
                value={rfqId}
                onChange={(e) => setRfqId(e.target.value)}
                disabled={!companyId}
                className="h-10 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)] disabled:opacity-50"
              >
                <option value="">Select an RFQ</option>
                {openRfqs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.rfq_number}: {r.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--bo-text-muted)]">Material</label>
              <select
                value={materialId}
                onChange={(e) => setMaterialId(e.target.value)}
                disabled={!rfqId}
                className="h-10 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)] disabled:opacity-50"
              >
                <option value="">Select a material</option>
                {rfqDetail?.items.map((i) => (
                  <option key={i.id} value={i.material_id}>
                    {i.material_name} ({i.quantity} {i.unit})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--bo-text-muted)]">Delivery area (optional)</label>
              <input
                value={area}
                onChange={(e) => setArea(e.target.value)}
                placeholder="e.g. Lahore"
                className="h-10 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
              />
            </div>
          </div>

          {companyId && rfqId && !materialId && (
            <p className="mt-3 text-sm text-[var(--bo-text-muted)]">Pick a material from the RFQ to see matching suppliers.</p>
          )}
        </div>

        {materialId && (
          <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
            <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Matching suppliers</h2>
            <p className="mt-0.5 text-xs text-[var(--bo-text-muted)]">
              Matched by {`a staff-confirmed material mapping (exact) or the supplier's declared category (approximate)`}, verified suppliers only.
            </p>

            {matchQuery.isError && (
              <div className="mt-4">
                <ErrorState error={matchQuery.error} onRetry={() => matchQuery.refetch()} />
              </div>
            )}
            {matchQuery.data && matchQuery.data.length === 0 && (
              <div className="mt-4">
                <EmptyState title="No eligible suppliers found" hint="Try a different material, or widen the delivery area." />
              </div>
            )}
            {matchQuery.data && matchQuery.data.length > 0 && (
              <div className="mt-4 overflow-x-auto rounded-lg border border-[var(--bo-divider)]">
                <table className="w-full text-sm">
                  <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                    <tr>
                      <th className="px-4 py-3">Supplier</th>
                      <th className="px-4 py-3">Product</th>
                      <th className="px-4 py-3">Price</th>
                      <th className="px-4 py-3">Min. qty</th>
                      <th className="px-4 py-3">Lead time</th>
                      <th className="px-4 py-3">Coverage</th>
                      <th className="px-4 py-3">Match basis</th>
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {matchQuery.data.map((m) => (
                      <tr key={m.product_id} className="h-14 border-t border-[var(--bo-divider)]">
                        <td className="px-4 py-3 font-medium text-[var(--bo-text)]">
                          {m.supplier_name}
                          <span className="ml-2 rounded-full bg-[var(--bo-success-bg)] px-2 py-0.5 text-xs font-medium text-[var(--bo-success)]">
                            Verified
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[var(--bo-text)]">{m.product_name}</td>
                        <td className="bo-tabular px-4 py-3 text-[var(--bo-text)]">{m.price}</td>
                        <td className="bo-tabular px-4 py-3 text-[var(--bo-text-muted)]">{m.minimum_order_quantity}</td>
                        <td className="px-4 py-3 text-[var(--bo-text-muted)]">{m.lead_time_days != null ? `${m.lead_time_days}d` : "—"}</td>
                        <td className="px-4 py-3 text-[var(--bo-text-muted)]">{m.coverage_areas.join(", ") || "—"}</td>
                        <td className="px-4 py-3 text-xs text-[var(--bo-text-muted)]">
                          {m.matched_via === "material_mapping" ? "Confirmed mapping" : "Category match"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            variant="secondary"
                            disabled={invite.isPending}
                            onClick={() => handleInvite(m.marketplace_supplier_id)}
                          >
                            Invite to RFQ
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </PlatformShell>
  );
}
