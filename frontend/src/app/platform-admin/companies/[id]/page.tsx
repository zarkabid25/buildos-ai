"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { usePlatformCompany, useSetCompanySuspended } from "@/lib/use-platform";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border py-2 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className="font-medium text-ink">{value}</span>
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

  return (
    <PlatformShell>
      <div className="max-w-2xl space-y-6">
        {companyLoading && (
          <Card>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="mt-4 h-4 w-full" />
            <Skeleton className="mt-2 h-4 w-full" />
          </Card>
        )}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {company && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h1 className="text-xl font-semibold text-ink">{company.name}</h1>
                <p className="text-sm text-muted">{company.code}</p>
              </div>
              <Button
                variant="secondary"
                disabled={setSuspended.isPending}
                onClick={handleToggle}
              >
                {company.is_active ? "Suspend company" : "Reactivate company"}
              </Button>
            </div>

            <Card>
              <Row
                label="Status"
                value={company.is_active ? "Active" : `Suspended${company.suspended_at ? ` on ${new Date(company.suspended_at).toLocaleDateString()}` : ""}`}
              />
              <Row label="Users" value={String(company.user_count)} />
              <Row label="Currency" value={company.currency} />
              <Row label="Email" value={company.email ?? "—"} />
              <Row label="Phone" value={company.phone ?? "—"} />
              <Row label="Created" value={new Date(company.created_at).toLocaleDateString()} />
            </Card>
          </>
        )}
      </div>
    </PlatformShell>
  );
}
