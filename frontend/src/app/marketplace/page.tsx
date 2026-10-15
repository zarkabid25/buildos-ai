"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import { useDiscoverSuppliers } from "@/lib/use-marketplace-discovery";

export default function MarketplacePage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [area, setArea] = useState("");

  const { data: suppliers, isLoading, isError, error, refetch } = useDiscoverSuppliers({
    search: search || undefined,
    category: category || undefined,
    area: area || undefined,
  });

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Supplier Marketplace</h1>
          <p className="text-muted">Verified suppliers across the BuildOS network.</p>
        </div>

        <Card>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Input placeholder="Search suppliers..." value={search} onChange={(e) => setSearch(e.target.value)} />
            <Input placeholder="Category (e.g. cement)" value={category} onChange={(e) => setCategory(e.target.value)} />
            <Input placeholder="Delivery area" value={area} onChange={(e) => setArea(e.target.value)} />
          </div>
        </Card>

        {isLoading && <TableSkeleton rows={4} />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {suppliers && suppliers.length === 0 && <EmptyState title="No suppliers found" hint="Try a different search or filter." />}

        {suppliers && suppliers.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {suppliers.map((supplier) => (
              <Link key={supplier.id} href={`/marketplace/${supplier.id}`}>
                <Card className="h-full transition-shadow hover:shadow-md">
                  <div className="flex items-start justify-between">
                    <h3 className="font-medium text-ink">{supplier.name}</h3>
                    <span className="rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success">Verified</span>
                  </div>
                  {supplier.is_connected && (
                    <span className="mt-1 inline-block rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                      {supplier.is_preferred ? "Preferred" : "Connected"}
                    </span>
                  )}
                  <p className="mt-2 text-sm text-muted">{supplier.categories.join(", ") || "No categories listed"}</p>
                  <p className="mt-1 text-sm text-muted">Delivers to: {supplier.coverage_areas.join(", ") || "Not specified"}</p>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
