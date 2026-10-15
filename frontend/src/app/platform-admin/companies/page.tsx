"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { PlatformShell } from "@/components/platform-shell";
import { useFeedback } from "@/components/feedback";
import { StatusBadge } from "@/components/platform/status-badge";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useApproveCompany, usePlatformCompanies, useSetCompanySuspended } from "@/lib/use-platform";
import { cn } from "@/lib/utils";

function RowSkeleton() {
  return (
    <tr className="border-b border-[var(--bo-divider)] last:border-0">
      <td className="px-4 py-4" colSpan={7}>
        <div className="h-4 w-full animate-pulse rounded bg-[var(--bo-nav-active)]" />
      </td>
    </tr>
  );
}

export default function PlatformCompaniesPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { confirm, toast } = useFeedback();
  const [search, setSearch] = useState("");

  const { data, isLoading: listLoading, isError, error, refetch } = usePlatformCompanies(search);
  const setSuspended = useSetCompanySuspended();
  const approveCompany = useApproveCompany();

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleToggle(id: string, name: string, suspend: boolean) {
    const ok = await confirm({
      title: suspend ? `Suspend ${name}?` : `Reactivate ${name}?`,
      body: suspend
        ? "Every user at this company will be signed out immediately and unable to log back in until reactivated."
        : "Users at this company will be able to log in again.",
      confirmLabel: suspend ? "Suspend" : "Reactivate",
      danger: suspend,
    });
    if (!ok) return;
    try {
      await setSuspended.mutateAsync({ id, suspend });
      toast(suspend ? `${name} suspended.` : `${name} reactivated.`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleApprove(id: string, name: string) {
    try {
      await approveCompany.mutateAsync(id);
      toast(`${name} approved.`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Companies">
      <div className="space-y-5">
        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Companies</h1>
              <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">
                {data ? `${data.total} ${data.total === 1 ? "company" : "companies"}` : "Every construction company using BuildOS AI."}
              </p>
            </div>
            <div className="flex h-10 w-full max-w-xs items-center gap-2 rounded-md border border-[var(--bo-border)] px-3 focus-within:ring-2 focus-within:ring-[var(--bo-focus)]">
              <Search className="h-4 w-4 shrink-0 text-[var(--bo-text-muted)]" />
              <label htmlFor="company-search" className="sr-only">
                Search by name or code
              </label>
              <input
                id="company-search"
                type="search"
                placeholder="Search by name or code..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-transparent text-sm text-[var(--bo-text)] placeholder:text-[var(--bo-text-muted)] focus:outline-none"
              />
            </div>
          </div>

          {isError && (
            <div className="mt-4">
              <ErrorState error={error} onRetry={() => refetch()} />
            </div>
          )}
          {data && data.companies.length === 0 && !isError && (
            <div className="mt-4">
              <EmptyState title="No companies found" hint={search ? "Try a different search." : undefined} />
            </div>
          )}

          {(listLoading || (data && data.companies.length > 0)) && !isError && (
            <div className="mt-4 overflow-x-auto rounded-lg border border-[var(--bo-divider)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                  <tr>
                    <th className="px-4 py-3">Company</th>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Users</th>
                    <th className="px-4 py-3">Currency</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Onboarding</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {listLoading &&
                    Array.from({ length: 5 }, (_, i) => <RowSkeleton key={i} />)}
                  {data?.companies.map((c) => (
                    <tr key={c.id} className="h-14 border-t border-[var(--bo-divider)]">
                      <td className="px-4 py-3">
                        <Link
                          href={`/platform-admin/companies/${c.id}`}
                          className="font-medium text-[var(--bo-primary)] hover:text-[var(--bo-primary-hover)]"
                        >
                          {c.name}
                        </Link>
                      </td>
                      <td className="bo-tabular px-4 py-3 text-[var(--bo-text-muted)]">{c.code}</td>
                      <td className="bo-tabular px-4 py-3 text-[var(--bo-text)]">{c.user_count}</td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{c.currency}</td>
                      <td className="px-4 py-3">
                        <StatusBadge active={c.is_active} />
                      </td>
                      <td className="px-4 py-3">
                        {c.onboarding_status === "approved" ? (
                          <span className="text-xs text-[var(--bo-success)]">Approved</span>
                        ) : (
                          <span className="text-xs text-[#8A5B09]">Pending</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          {c.onboarding_status === "pending" && (
                            <button
                              disabled={approveCompany.isPending}
                              onClick={() => handleApprove(c.id, c.name)}
                              className="h-9 rounded-md bg-[var(--bo-primary)] px-3 text-sm font-medium text-[var(--bo-on-primary)] hover:bg-[var(--bo-primary-hover)]"
                            >
                              Approve
                            </button>
                          )}
                          <button
                            disabled={setSuspended.isPending}
                            onClick={() => handleToggle(c.id, c.name, c.is_active)}
                            className={cn(
                              "h-9 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm font-medium text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]",
                              setSuspended.isPending && "cursor-not-allowed opacity-60"
                            )}
                          >
                            {c.is_active ? "Suspend" : "Reactivate"}
                          </button>
                        </div>
                      </td>
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
