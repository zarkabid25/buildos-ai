"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Search } from "lucide-react";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState } from "@/components/ui/states";
import type { MarketplaceSupplierStatus } from "@/lib/marketplace-types";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useCreateMarketplaceSupplier, useMarketplaceSuppliers } from "@/lib/use-marketplace";

const STATUS_STYLE: Record<MarketplaceSupplierStatus, string> = {
  pending: "bg-[#FFF6DE] text-[#8A5B09]",
  verified: "bg-[var(--bo-success-bg)] text-[var(--bo-success)]",
  rejected: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
  suspended: "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]",
};

const createSchema = z.object({
  name: z.string().trim().min(1, "Name is required"),
  email: z.string().trim().email("Enter a valid email").optional().or(z.literal("")),
  categories: z.string().trim().optional(),
  coverage_areas: z.string().trim().optional(),
});
type CreateInput = z.infer<typeof createSchema>;

export default function MarketplaceSuppliersPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<MarketplaceSupplierStatus | "">("");
  const [showForm, setShowForm] = useState(false);
  const isReadOnly = admin?.role === "support";

  const { data, isLoading: listLoading, isError, error, refetch } = useMarketplaceSuppliers({
    search: search || undefined,
    verification_status: status || undefined,
  });
  const createSupplier = useCreateMarketplaceSupplier();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateInput>({ resolver: zodResolver(createSchema) });

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function onCreate(values: CreateInput) {
    try {
      const result = await createSupplier.mutateAsync({
        name: values.name,
        email: values.email || undefined,
        categories: values.categories ? values.categories.split(",").map((c) => c.trim()).filter(Boolean) : [],
        coverage_areas: values.coverage_areas ? values.coverage_areas.split(",").map((a) => a.trim()).filter(Boolean) : [],
      });
      reset();
      setShowForm(false);
      if (result.possible_duplicates.length > 0) {
        toast(
          `Added, but ${result.possible_duplicates.length} supplier(s) with the same name already exist -- review before relying on this as a new one.`,
          "info"
        );
      } else {
        toast("Supplier added.", "success");
      }
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Marketplace">
      <div className="space-y-5">
        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Supplier Registry</h1>
              <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">
                {data ? `${data.total} ${data.total === 1 ? "supplier" : "suppliers"}` : "The global marketplace supplier registry."}
              </p>
            </div>
            {!isReadOnly && <Button onClick={() => setShowForm((s) => !s)}>Add supplier</Button>}
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <div className="flex h-10 flex-1 min-w-[200px] items-center gap-2 rounded-md border border-[var(--bo-border)] px-3">
              <Search className="h-4 w-4 shrink-0 text-[var(--bo-text-muted)]" />
              <input
                type="search"
                placeholder="Search by name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-transparent text-sm text-[var(--bo-text)] placeholder:text-[var(--bo-text-muted)] focus:outline-none"
              />
            </div>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as MarketplaceSupplierStatus | "")}
              className="h-10 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
            >
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="verified">Verified</option>
              <option value="rejected">Rejected</option>
              <option value="suspended">Suspended</option>
            </select>
          </div>

          {showForm && (
            <form onSubmit={handleSubmit(onCreate)} className="mt-4 grid gap-3 border-t border-[var(--bo-divider)] pt-4 sm:grid-cols-5">
              <div>
                <Label htmlFor="name">Name</Label>
                <Input id="name" {...register("name")} />
                {errors.name && <p className="mt-1 text-xs text-danger">{errors.name.message}</p>}
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" {...register("email")} />
              </div>
              <div>
                <Label htmlFor="categories">Categories</Label>
                <Input id="categories" placeholder="cement, steel" {...register("categories")} />
              </div>
              <div>
                <Label htmlFor="coverage_areas">Coverage</Label>
                <Input id="coverage_areas" placeholder="Punjab, Sindh" {...register("coverage_areas")} />
              </div>
              <div className="flex items-end">
                <Button type="submit" disabled={isSubmitting} className="w-full">
                  {isSubmitting ? "Adding..." : "Add"}
                </Button>
              </div>
            </form>
          )}
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {data && data.suppliers.length === 0 && !isError && <EmptyState title="No suppliers found" />}

        {data && data.suppliers.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Categories</th>
                  <th className="px-4 py-3">Coverage</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Onboarded by</th>
                </tr>
              </thead>
              <tbody>
                {data.suppliers.map((s) => (
                  <tr key={s.id} className="h-14 border-t border-[var(--bo-divider)]">
                    <td className="px-4 py-3">
                      <Link href={`/platform-admin/marketplace/${s.id}`} className="font-medium text-[var(--bo-primary)]">
                        {s.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{s.categories.join(", ") || "—"}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{s.coverage_areas.join(", ") || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[s.verification_status]}`}>
                        {s.verification_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{s.onboarded_by_name ?? "—"}</td>
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
