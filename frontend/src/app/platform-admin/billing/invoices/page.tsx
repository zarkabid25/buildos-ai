"use client";

import { Fragment, useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import { PlatformShell } from "@/components/platform-shell";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState } from "@/components/ui/states";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useAdminInvoices, useBillingCompanies } from "@/lib/use-platform-billing";

const STATUS_CLASSES: Record<string, string> = {
  draft: "bg-gray-100 text-[var(--bo-text-muted)]",
  pending: "bg-amber-50 text-[var(--bo-warning)]",
  paid: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  rejected: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
  void: "bg-gray-100 text-[var(--bo-text-muted)]",
};

const PAYMENT_STATUS_CLASSES: Record<string, string> = {
  pending: "bg-amber-50 text-[var(--bo-warning)]",
  verified: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  rejected: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
};

export default function PlatformBillingInvoicesPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const [companyId, setCompanyId] = useState("");
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: companies } = useBillingCompanies({});
  const { data: invoices, isLoading: listLoading, isError, error, refetch } = useAdminInvoices({
    company_id: companyId || undefined,
    status: status || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  const outstanding = invoices?.filter((i) => i.status === "pending").reduce((sum, i) => sum + Number(i.total_amount), 0) ?? 0;

  return (
    <PlatformShell breadcrumb="Invoices">
      <div className="space-y-5">
        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Invoice Management</h1>
              <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">
                {invoices ? `${invoices.length} invoice(s)` : "Every subscription invoice, platform-wide."}
                {outstanding > 0 && ` · $${outstanding.toFixed(2)} outstanding in this view`}
              </p>
            </div>
          </div>

          <div className="mt-4 grid gap-3 border-t border-[var(--bo-divider)] pt-4 sm:grid-cols-4">
            <div>
              <Label htmlFor="inv-company">Company</Label>
              <select
                id="inv-company"
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
                className="h-10 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
              >
                <option value="">All companies</option>
                {companies?.map((c) => (
                  <option key={c.company_id} value={c.company_id}>{c.company_name}</option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="inv-status">Status</Label>
              <select
                id="inv-status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="h-10 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
              >
                <option value="">All statuses</option>
                {Object.keys(STATUS_CLASSES).map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="inv-from">From</Label>
              <Input id="inv-from" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="inv-to">To</Label>
              <Input id="inv-to" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </div>
          </div>
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {!listLoading && invoices && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Invoice</th>
                  <th className="px-4 py-3">Company</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Due</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {invoices.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-[var(--bo-text-muted)]">No invoices match these filters.</td>
                  </tr>
                )}
                {invoices.map((inv) => (
                  <Fragment key={inv.id}>
                    <tr className="h-14 border-t border-[var(--bo-divider)]">
                      <td className="px-4 py-3 font-medium text-[var(--bo-text)]">{inv.invoice_number}</td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{inv.company_name ?? "—"}</td>
                      <td className="bo-tabular px-4 py-3 text-[var(--bo-text)]">{inv.total_amount} {inv.currency}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[inv.status]}`}>{inv.status}</span>
                      </td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{inv.due_date}</td>
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
                              <h3 className="text-xs font-medium text-[var(--bo-text-muted)]">Payment submissions</h3>
                              {inv.payments.length === 0 && <p className="mt-2 text-sm text-[var(--bo-text-muted)]">No payment submitted yet.</p>}
                              <ul className="mt-2 space-y-1">
                                {inv.payments.map((p) => (
                                  <li key={p.id} className="flex items-center justify-between text-sm">
                                    <span className="text-[var(--bo-text)]">{p.amount} &middot; {p.reference ?? "no reference"}</span>
                                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PAYMENT_STATUS_CLASSES[p.status]}`}>{p.status}</span>
                                  </li>
                                ))}
                              </ul>
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
