"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import {
  useCompanyBillingSummary,
  useCompanySubscriptionEvents,
  useCompanySubscriptions,
  useEnterGracePeriod,
  useExpireSubscription,
} from "@/lib/use-platform-billing";

const STATUS_CLASSES: Record<string, string> = {
  trialing: "bg-amber-50 text-[var(--bo-warning)]",
  active: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  pending_payment: "bg-amber-50 text-[var(--bo-warning)]",
  grace_period: "bg-amber-50 text-[var(--bo-warning)]",
  cancelled: "bg-gray-100 text-[var(--bo-text-muted)]",
  expired: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
};

export default function PlatformCompanySubscriptionDetailPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const params = useParams<{ companyId: string }>();
  const { toast, confirm } = useFeedback();
  const isReadOnly = admin?.role === "support";

  const { data: summary, isLoading: summaryLoading, isError, error, refetch } = useCompanyBillingSummary(params.companyId);
  const { data: history } = useCompanySubscriptions(params.companyId);
  const { data: events } = useCompanySubscriptionEvents(params.companyId);
  const enterGrace = useEnterGracePeriod(params.companyId);
  const expire = useExpireSubscription(params.companyId);

  const liveSub = history?.find((s) => ["trialing", "active", "pending_payment", "grace_period"].includes(s.status));

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleGracePeriod() {
    if (!liveSub) return;
    const ok = await confirm({ title: "Move to grace period?", body: "The company keeps access while the grace period runs, but billing status will show as overdue.", confirmLabel: "Start grace period" });
    if (!ok) return;
    try {
      await enterGrace.mutateAsync(liveSub.id);
      toast("Subscription moved to grace period.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleExpire() {
    if (!liveSub) return;
    const ok = await confirm({ title: "Expire this subscription?", body: "The company's historical ERP data stays intact -- this only ends the subscription's access to plan-gated limits.", confirmLabel: "Expire", danger: true });
    if (!ok) return;
    try {
      await expire.mutateAsync(liveSub.id);
      toast("Subscription expired.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Subscriptions">
      <div className="max-w-3xl space-y-5">
        {summaryLoading && (
          <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5">
            <Skeleton className="h-6 w-48" />
          </div>
        )}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {summary && (
          <>
            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h1 className="text-[17px] font-medium text-[var(--bo-text)]">{summary.company_name}</h1>
                  <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">{summary.plan_name ?? "No plan"}</p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[summary.status] ?? "bg-gray-100 text-[var(--bo-text-muted)]"}`}>
                  {summary.status.replace("_", " ")}
                </span>
              </div>
              {summary.is_legacy && (
                <p className="mt-3 rounded-md bg-[var(--bo-nav-active)] px-3 py-2 text-xs text-[var(--bo-text-secondary)]">
                  Grandfathered: this company has an explicit legacy entitlement from before Phase 5 and is never auto-charged or newly restricted.
                </p>
              )}
              <dl className="mt-4 grid grid-cols-3 gap-4 text-sm">
                <div>
                  <dt className="text-xs text-[var(--bo-text-muted)]">Trial ends</dt>
                  <dd className="text-[var(--bo-text)]">{summary.trial_ends_at ? new Date(summary.trial_ends_at).toLocaleDateString() : "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-[var(--bo-text-muted)]">Renews / expires</dt>
                  <dd className="text-[var(--bo-text)]">{summary.current_period_end ? new Date(summary.current_period_end).toLocaleDateString() : "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-[var(--bo-text-muted)]">Grace ends</dt>
                  <dd className="text-[var(--bo-text)]">{summary.grace_period_ends_at ? new Date(summary.grace_period_ends_at).toLocaleDateString() : "—"}</dd>
                </div>
              </dl>
              {!isReadOnly && liveSub && (liveSub.status === "active" || liveSub.status === "pending_payment" || liveSub.status === "grace_period") && (
                <div className="mt-4 flex gap-2 border-t border-[var(--bo-divider)] pt-4">
                  {liveSub.status !== "grace_period" && (
                    <button onClick={handleGracePeriod} className="h-9 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm font-medium text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]">
                      Move to grace period
                    </button>
                  )}
                  <button onClick={handleExpire} className="h-9 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm font-medium text-[var(--bo-danger)] hover:bg-[var(--bo-surface-hover)]">
                    Expire subscription
                  </button>
                </div>
              )}
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <h2 className="text-[15px] font-medium text-[var(--bo-text)]">Plan history</h2>
              <ul className="mt-3 space-y-2">
                {history?.map((s) => (
                  <li key={s.id} className="flex items-center justify-between rounded-md border border-[var(--bo-divider)] px-3 py-2 text-sm">
                    <span className="text-[var(--bo-text)]">{s.plan_name} &middot; {s.billing_period}</span>
                    <span className="text-xs text-[var(--bo-text-muted)]">{s.status.replace("_", " ")} &middot; {new Date(s.created_at).toLocaleDateString()}</span>
                  </li>
                ))}
                {history?.length === 0 && <p className="text-sm text-[var(--bo-text-muted)]">No subscription history.</p>}
              </ul>
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <h2 className="text-[15px] font-medium text-[var(--bo-text)]">Activity history</h2>
              <ul className="mt-3 space-y-3 border-l border-[var(--bo-divider)] pl-4">
                {events?.map((e) => (
                  <li key={e.id} className="relative text-sm">
                    <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-[var(--bo-primary)]" />
                    <p className="text-[var(--bo-text)]">{e.summary}</p>
                    <p className="text-xs text-[var(--bo-text-muted)]">
                      {new Date(e.created_at).toLocaleString()}
                      {e.actor_staff_name ? ` · ${e.actor_staff_name} (staff)` : e.actor_user_name ? ` · ${e.actor_user_name}` : ""}
                    </p>
                  </li>
                ))}
                {events?.length === 0 && <p className="text-sm text-[var(--bo-text-muted)]">No recorded activity yet.</p>}
              </ul>
            </div>
          </>
        )}
      </div>
    </PlatformShell>
  );
}
