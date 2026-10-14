"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PlatformShell } from "@/components/platform-shell";
import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { usePlatformCompanies, useSetCompanySuspended } from "@/lib/use-platform";

export default function PlatformCompaniesPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { confirm, toast } = useFeedback();
  const [search, setSearch] = useState("");

  const { data, isLoading: listLoading, isError, error, refetch } = usePlatformCompanies(search);
  const setSuspended = useSetCompanySuspended();

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

  return (
    <PlatformShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-ink">Companies</h1>
            <p className="text-sm text-muted">Every construction company using BuildOS AI.</p>
          </div>
          <Input
            placeholder="Search by name or code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
        </div>

        {listLoading && <TableSkeleton rows={6} />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {data && data.companies.length === 0 && (
          <EmptyState title="No companies found" hint={search ? "Try a different search." : undefined} />
        )}
        {data && data.companies.length > 0 && (
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead className="border-b border-border text-left text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Company</th>
                  <th className="px-4 py-3 font-medium">Code</th>
                  <th className="px-4 py-3 font-medium">Users</th>
                  <th className="px-4 py-3 font-medium">Currency</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {data.companies.map((c) => (
                  <tr key={c.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3">
                      <Link href={`/platform-admin/companies/${c.id}`} className="font-medium text-primary">
                        {c.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted">{c.code}</td>
                    <td className="px-4 py-3">{c.user_count}</td>
                    <td className="px-4 py-3 text-muted">{c.currency}</td>
                    <td className="px-4 py-3">
                      {c.is_active ? (
                        <span className="rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
                          Active
                        </span>
                      ) : (
                        <span className="rounded-full bg-danger/10 px-2 py-0.5 text-xs font-medium text-danger">
                          Suspended
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="secondary"
                        disabled={setSuspended.isPending}
                        onClick={() => handleToggle(c.id, c.name, c.is_active)}
                      >
                        {c.is_active ? "Suspend" : "Reactivate"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </PlatformShell>
  );
}
