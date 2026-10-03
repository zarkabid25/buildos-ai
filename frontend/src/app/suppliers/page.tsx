"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { SupplierActivityPanel } from "@/components/supplier-activity-panel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import { attempt } from "@/lib/utils";
import { useCreateSupplier, useSuppliers } from "@/lib/use-suppliers";

export default function SuppliersPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const { data: suppliers, isLoading, isError, error, refetch } = useSuppliers();
  const createSupplier = useCreateSupplier();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", phone: "", email: "", address: "" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = suppliers?.find((s) => s.id === selectedId);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  async function handleCreate() {
    if (!form.name.trim()) return;
    if (!(await attempt(createSupplier.mutateAsync(form)))) return;
    setForm({ name: "", phone: "", email: "", address: "" });
    setShowForm(false);
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-ink">Suppliers</h1>
            <p className="text-muted">Vendors and contacts for procurement.</p>
          </div>
          <Button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "+ New Supplier"}</Button>
        </div>

        {showForm && (
          <Card>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <Input placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              <Input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              <Input placeholder="Address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </div>
            <Button className="mt-3" onClick={handleCreate} disabled={createSupplier.isPending}>
              Add supplier
            </Button>
          </Card>
        )}

        {isLoading && <TableSkeleton />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}

        {!isLoading && suppliers && suppliers.length === 0 && (
          <EmptyState title="No suppliers yet" hint="Add your first vendor above." />
        )}

        {!isLoading && suppliers && suppliers.length > 0 && (
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Phone</th>
                  <th className="px-4 py-3 font-medium">Email</th>
                  <th className="px-4 py-3 font-medium">Address</th>
                </tr>
              </thead>
              <tbody>
                {suppliers.map((s) => (
                  <tr
                    key={s.id}
                    className={`border-b border-border last:border-0 ${s.id === selectedId ? "bg-blue-50/60" : ""}`}
                  >
                    <td className="px-4 py-3 font-medium">
                      <button className="text-left text-ink hover:text-primary" onClick={() => setSelectedId(s.id)}>
                        {s.name}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-muted">{s.phone ?? "—"}</td>
                    <td className="px-4 py-3 text-muted">{s.email ?? "—"}</td>
                    <td className="px-4 py-3 text-muted">{s.address ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}

        {selected ? (
          <SupplierActivityPanel supplierId={selected.id} supplierName={selected.name} />
        ) : (
          suppliers &&
          suppliers.length > 0 && (
            <p className="text-sm text-muted">Select a supplier to see its purchase orders and performance.</p>
          )
        )}
      </div>
    </AppShell>
  );
}
