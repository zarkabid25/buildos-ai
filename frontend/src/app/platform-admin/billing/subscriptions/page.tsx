"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { PlatformShell } from "@/components/platform-shell";
import { ErrorState } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useBillingCompanies, usePlatformPlans } from "@/lib/use-platform-billing";

const STATUS_CLASSES: Record<string, string> = {
  trialing: "bg-amber-50 text-[var(--bo-warning)]",
  active: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  pending_payment: "bg-amber-50 text-[var(--bo-warning)]",
  grace_period: "bg-amber-50 text-[var(--bo-warning)]",
  cancelled: "bg-gray-100 text-[var(--bo-text-muted)]",
  expired: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
  legacy: "bg-[var(--bo-nav-active)] text-[var(--bo-text-secondary)]",
  none: "bg-gray-100 text-[var(--bo-text-muted)]",
};

const STATUS_LABELS: Record<string, string> = {
  trialing: "Trialing",
  active: "Active",
  pending_payment: "Pending payment",
  grace_period: "Grace period",
  cancelled: "Cancelled",
  expired: "Expired",
  legacy: "Legacy (grandfathered)",
  none: "No subscription",
};

export default function PlatformBillingSubscriptionsPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [planId, setPlanId] = useState("");
  const [status, setStatus] = useState("");

  const { data: plans } = usePlatformPlans(true);
  const { data: companies, isLoading: listLoading, isError, error, refetch } = useBillingCompanies({ search, plan_id: planId || undefined, status: status || undefined });

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  return (
    <PlatformShell breadcrumb="Subscriptions">
      <div className="space-y-5">
        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Company Subscriptions</h1>
              <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">Every company's current plan, billing status and renewal dates.</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex h-10 w-56 items-center gap-2 rounded-md border border-[var(--bo-border)] px-3 focus-within:ring-2 focus-within:ring-[var(--bo-focus)]">
                <Search className="h-4 w-4 shrink-0 text-[var(--bo-text-muted)]" />
                <label htmlFor="billing-search" className="sr-only">Search by company</label>
                <input
                  id="billing-search"
                  type="search"
                  placeholder="Search by company..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-transparent text-sm text-[var(--bo-text)] placeholder:text-[var(--bo-text-muted)] focus:outline-none"
                />
              </div>
              <select
                value={planId}
                onChange={(e) => setPlanId(e.target.value)}
                className="h-10 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
              >
                <option value="">All plans</option>
                {plans?.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="h-10 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
              >
                <option value="">All statuses</option>
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {!listLoading && companies && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Company</th>
                  <th className="px-4 py-3">Plan</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Trial ends</th>
                  <th className="px-4 py-3">Renews / expires</th>
                  <th className="px-4 py-3">Grace ends</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {companies.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-sm text-[var(--bo-text-muted)]">No companies match these filters.</td>
                  </tr>
                )}
                {companies.map((c) => (
                  <tr key={c.company_id} className="h-14 border-t border-[var(--bo-divider)]">
                    <td className="px-4 py-3 font-medium text-[var(--bo-text)]">{c.company_name}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{c.plan_name ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[c.status] ?? "bg-gray-100 text-[var(--bo-text-muted)]"}`}>
                        {STATUS_LABELS[c.status] ?? c.status}
                        {c.is_legacy && c.status !== "legacy" ? " · legacy" : ""}
                      </span>
                    </td>
                    <td className="bo-tabular px-4 py-3 text-[var(--bo-text-muted)]">{c.trial_ends_at ? new Date(c.trial_ends_at).toLocaleDateString() : "—"}</td>
                    <td className="bo-tabular px-4 py-3 text-[var(--bo-text-muted)]">{c.current_period_end ? new Date(c.current_period_end).toLocaleDateString() : "—"}</td>
                    <td className="bo-tabular px-4 py-3 text-[var(--bo-text-muted)]">{c.grace_period_ends_at ? new Date(c.grace_period_ends_at).toLocaleDateString() : "—"}</td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/platform-admin/billing/subscriptions/${c.company_id}`} className="text-xs font-medium text-[var(--bo-primary)] hover:underline">
                        View detail
                      </Link>
                    </td>
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
