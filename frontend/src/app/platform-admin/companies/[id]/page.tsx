"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { StatusBadge } from "@/components/platform/status-badge";
import { PlatformShell } from "@/components/platform-shell";
import { ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useApproveCompany, usePlatformCompany, useSetCompanySuspended } from "@/lib/use-platform";
import { cn } from "@/lib/utils";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between border-t border-[var(--bo-divider)] py-3 text-sm first:border-0">
      <span className="text-[var(--bo-text-muted)]">{label}</span>
      <span className="bo-tabular font-medium text-[var(--bo-text)]">{value}</span>
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5">
      <div className="h-6 w-48 animate-pulse rounded bg-[var(--bo-nav-active)]" />
      <div className="mt-4 h-4 w-full animate-pulse rounded bg-[var(--bo-nav-active)]" />
      <div className="mt-2 h-4 w-full animate-pulse rounded bg-[var(--bo-nav-active)]" />
    </div>
  );
}

export default function PlatformCompanyDetailPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { confirm, toast } = useFeedback();

  const { data: company, isLoading: companyLoading, isError, error, refetch } = usePlatformCompany(params.id);
  const setSuspended = useSetCompanySuspended();
  const approveCompany = useApproveCompany();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleToggle() {
    if (!company) return;
    const suspend = company.is_active;
    const ok = await confirm({
      title: suspend ? `Suspend ${company.name}?` : `Reactivate ${company.name}?`,
      body: suspend
        ? "Every user at this company will be signed out immediately and unable to log back in until reactivated."
        : "Users at this company will be able to log in again.",
      confirmLabel: suspend ? "Suspend" : "Reactivate",
      danger: suspend,
    });
    if (!ok) return;
    try {
      await setSuspended.mutateAsync({ id: company.id, suspend });
      toast(suspend ? `${company.name} suspended.` : `${company.name} reactivated.`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleApprove() {
    if (!company) return;
    try {
      await approveCompany.mutateAsync(company.id);
      toast(`${company.name} approved.`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb={company ? company.name : "Companies"}>
      <div className="max-w-2xl space-y-5">
        {companyLoading && <CardSkeleton />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {company && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold tracking-[-0.025em] text-[var(--bo-text)]">{company.name}</h1>
                <p className="text-sm text-[var(--bo-text-muted)]">{company.code}</p>
              </div>
              <div className="flex gap-2">
                {company.onboarding_status === "pending" && (
                  <button
                    disabled={approveCompany.isPending}
                    onClick={handleApprove}
                    className={cn(
                      "h-10 rounded-md bg-[var(--bo-primary)] px-4 text-sm font-medium text-[var(--bo-on-primary)] hover:bg-[var(--bo-primary-hover)]",
                      approveCompany.isPending && "cursor-not-allowed opacity-60"
                    )}
                  >
                    Approve company
                  </button>
                )}
                <button
                  disabled={setSuspended.isPending}
                  onClick={handleToggle}
                  className={cn(
                    "h-10 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-4 text-sm font-medium text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]",
                    setSuspended.isPending && "cursor-not-allowed opacity-60"
                  )}
                >
                  {company.is_active ? "Suspend company" : "Reactivate company"}
                </button>
              </div>
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <Row
                label="Status"
                value={
                  <span className="flex items-center gap-2">
                    <StatusBadge active={company.is_active} />
                    {!company.is_active && company.suspended_at && (
                      <span className="font-normal text-[var(--bo-text-muted)]">
                        since {new Date(company.suspended_at).toLocaleDateString()}
                      </span>
                    )}
                  </span>
                }
              />
              <Row
                label="Onboarding"
                value={
                  company.onboarding_status === "approved" ? (
                    <span className="text-[var(--bo-success)]">Approved</span>
                  ) : (
                    <span className="text-[#8A5B09]">Pending review</span>
                  )
                }
              />
              <Row label="Users" value={company.user_count} />
              <Row label="Currency" value={company.currency} />
              <Row label="Email" value={company.email ?? "—"} />
              <Row label="Phone" value={company.phone ?? "—"} />
              <Row label="Created" value={new Date(company.created_at).toLocaleDateString()} />
            </div>
          </>
        )}
      </div>
    </PlatformShell>
  );
}
