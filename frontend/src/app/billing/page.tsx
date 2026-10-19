"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import type { UserRole } from "@/lib/auth-types";
import type { BillingPeriod } from "@/lib/billing-types";
import { ApiError } from "@/lib/api";
import {
  useAvailablePlans,
  useCancelSubscription,
  useChangePlan,
  useCreateSubscription,
  useCurrentSubscription,
  useEntitlements,
  useInvoices,
} from "@/lib/use-billing";
import { attempt } from "@/lib/utils";

const CAN_MANAGE: UserRole[] = ["super_admin", "company_admin"];

const STATUS_CLASSES: Record<string, string> = {
  trialing: "bg-blue-50 text-primary",
  active: "bg-green-50 text-success",
  pending_payment: "bg-amber-50 text-warning",
  grace_period: "bg-amber-50 text-warning",
  cancelled: "bg-gray-100 text-muted",
  expired: "bg-red-50 text-danger",
};

export default function BillingPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const { toast, confirm } = useFeedback();
  const canManage = !!user && CAN_MANAGE.includes(user.role);

  const subQuery = useCurrentSubscription();
  const plansQuery = useAvailablePlans();
  const entitlementsQuery = useEntitlements();
  const invoicesQuery = useInvoices();
  const createSub = useCreateSubscription();
  const changePlan = useChangePlan(subQuery.data?.id ?? "");
  const cancelSub = useCancelSubscription(subQuery.data?.id ?? "");
  const [period, setPeriod] = useState<BillingPeriod>("monthly");

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) return null;

  async function handleSubscribe(planId: string) {
    const ok = await attempt(createSub.mutateAsync({ plan_id: planId, billing_period: period, currency: "USD" }));
    if (ok) toast("Subscribed. Check Billing History for your first invoice.", "success");
  }

  async function handleChangePlan(planId: string) {
    const ok = await attempt(changePlan.mutateAsync(planId));
    if (ok) toast("Plan changed.", "success");
  }

  async function handleCancel() {
    const okConfirm = await confirm({ title: "Cancel your subscription?", body: "You can start a new one at any time.", confirmLabel: "Cancel subscription", danger: true });
    if (!okConfirm) return;
    try {
      await cancelSub.mutateAsync();
      toast("Subscription cancelled.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  const sub = subQuery.data;
  const ent = entitlementsQuery.data;

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Billing &amp; Subscription</h1>
          <p className="text-muted">Your plan, usage, and payment history.</p>
        </div>

        <Card className="space-y-3">
          <h2 className="text-sm font-semibold text-ink">Current subscription</h2>
          {subQuery.isLoading && <TableSkeleton rows={2} />}
          {!subQuery.isLoading && !sub && <EmptyState title="No active subscription" hint="Pick a plan below to get started." />}
          {sub && (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-lg font-medium text-ink">{sub.plan_name}</p>
                <p className="text-sm text-muted">
                  {sub.billing_period} &middot; {sub.trial_ends_at && sub.status === "trialing" ? `trial ends ${sub.trial_ends_at.slice(0, 10)}` : sub.current_period_end ? `renews ${sub.current_period_end.slice(0, 10)}` : ""}
                  {sub.status === "grace_period" && sub.grace_period_ends_at && ` · grace period ends ${sub.grace_period_ends_at.slice(0, 10)}`}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_CLASSES[sub.status] ?? ""}`}>{sub.status.replace("_", " ")}</span>
                {canManage && sub.status !== "cancelled" && sub.status !== "expired" && (
                  <Button variant="ghost" className="text-muted hover:text-danger" onClick={handleCancel}>
                    Cancel
                  </Button>
                )}
              </div>
            </div>
          )}
        </Card>

        {ent && (
          <Card className="space-y-2">
            <h2 className="text-sm font-semibold text-ink">Usage &amp; plan limits</h2>
            <p className="text-xs text-muted">
              {ent.source === "legacy" ? "Grandfathered access -- no plan limits apply." : ent.source === "none" ? "No subscription yet -- unrestricted for now." : `On the ${ent.plan_name} plan.`}
            </p>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Usage label="Projects" current={ent.current_projects} max={ent.max_projects} />
              <Usage label="Team members" current={ent.current_team_members} max={ent.max_team_members} />
              <div>
                <p className="text-xs text-muted">Marketplace</p>
                <p className="text-sm font-medium text-ink">{ent.marketplace_included ? "Included" : "Not included"}</p>
              </div>
              <div>
                <p className="text-xs text-muted">Storage</p>
                <p className="text-sm font-medium text-ink">{ent.storage_gb != null ? `${ent.storage_gb} GB` : "Unlimited"}</p>
              </div>
            </div>
          </Card>
        )}

        {canManage && (
          <Card className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink">Available plans</h2>
              <div className="flex rounded-md border border-border p-0.5 text-xs">
                <button className={`rounded px-2 py-1 ${period === "monthly" ? "bg-background font-medium text-ink" : "text-muted"}`} onClick={() => setPeriod("monthly")}>
                  Monthly
                </button>
                <button className={`rounded px-2 py-1 ${period === "annual" ? "bg-background font-medium text-ink" : "text-muted"}`} onClick={() => setPeriod("annual")}>
                  Annual
                </button>
              </div>
            </div>
            {plansQuery.isLoading && <TableSkeleton rows={3} />}
            {plansQuery.isError && <ErrorState error={plansQuery.error} onRetry={() => plansQuery.refetch()} />}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {plansQuery.data?.map((plan) => {
                const price = plan.prices.find((p) => p.billing_period === period && p.is_current);
                const isCurrent = sub?.plan_id === plan.id;
                return (
                  <div key={plan.id} className="rounded-card border border-border p-4">
                    <p className="font-medium text-ink">{plan.name}</p>
                    <p className="mt-1 text-xl font-semibold text-ink">
                      {price ? `${price.amount} ${price.currency}` : "—"}
                      <span className="text-xs font-normal text-muted">/{period === "monthly" ? "mo" : "yr"}</span>
                    </p>
                    <ul className="mt-2 space-y-0.5 text-xs text-muted">
                      <li>{plan.max_projects != null ? `${plan.max_projects} projects` : "Unlimited projects"}</li>
                      <li>{plan.max_team_members != null ? `${plan.max_team_members} team members` : "Unlimited team members"}</li>
                      <li>{plan.marketplace_included ? "Marketplace included" : "No marketplace access"}</li>
                      {plan.trial_days > 0 && <li>{plan.trial_days}-day free trial</li>}
                    </ul>
                    <Button
                      className="mt-3 w-full"
                      variant={isCurrent ? "secondary" : "primary"}
                      disabled={isCurrent || createSub.isPending || changePlan.isPending}
                      onClick={() => (sub ? handleChangePlan(plan.id) : handleSubscribe(plan.id))}
                    >
                      {isCurrent ? "Current plan" : sub ? "Switch to this plan" : "Subscribe"}
                    </Button>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">Billing history</h2>
          </div>
          {invoicesQuery.isLoading && <TableSkeleton rows={3} />}
          {invoicesQuery.isError && <ErrorState error={invoicesQuery.error} onRetry={() => invoicesQuery.refetch()} />}
          {invoicesQuery.data && invoicesQuery.data.length === 0 && <EmptyState title="No invoices yet" />}
          {invoicesQuery.data && invoicesQuery.data.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                  <th className="py-2 pr-4 font-medium">Invoice</th>
                  <th className="py-2 pr-4 font-medium">Period</th>
                  <th className="py-2 pr-4 font-medium">Amount</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 pr-4 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {invoicesQuery.data.map((inv) => (
                  <tr key={inv.id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-4 font-medium text-ink">{inv.invoice_number}</td>
                    <td className="py-2 pr-4 text-muted">{inv.billing_period_start} &ndash; {inv.billing_period_end}</td>
                    <td className="py-2 pr-4">{inv.total_amount} {inv.currency}</td>
                    <td className="py-2 pr-4">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_CLASSES[inv.status] ?? "bg-gray-100 text-muted"}`}>{inv.status}</span>
                    </td>
                    <td className="py-2 pr-4 text-right">
                      <Link href={`/billing/invoices/${inv.id}`} className="font-medium text-primary hover:underline">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </AppShell>
  );
}

function Usage({ label, current, max }: { label: string; current: number; max: number | null }) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-sm font-medium text-ink">
        {current} {max != null ? `/ ${max}` : "(unlimited)"}
      </p>
    </div>
  );
}
