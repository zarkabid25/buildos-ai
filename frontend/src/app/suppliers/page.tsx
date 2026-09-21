"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth-context";
import { useCreateSupplier, useSuppliers } from "@/lib/use-suppliers";

export default function SuppliersPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const { data: suppliers, isLoading } = useSuppliers();
  const createSupplier = useCreateSupplier();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", phone: "", email: "", address: "" });

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  async function handleCreate() {
    if (!form.name.trim()) return;
    await createSupplier.mutateAsync(form);
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

        {isLoading && <p className="text-sm text-muted">Loading suppliers...</p>}

        {!isLoading && suppliers && suppliers.length === 0 && (
          <Card className="text-center text-sm text-muted">
            No suppliers yet. Add your first vendor above.
          </Card>
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
                  <tr key={s.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3 font-medium text-ink">{s.name}</td>
                    <td className="px-4 py-3 text-muted">{s.phone ?? "—"}</td>
                    <td className="px-4 py-3 text-muted">{s.email ?? "—"}</td>
                    <td className="px-4 py-3 text-muted">{s.address ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}

        <Card className="border-border bg-gray-50/60 text-sm text-muted">
          Performance scoring (price/quality/delivery/reliability) and order history will appear
          here once Purchase Orders are built — those numbers need real order data behind them,
          not placeholders.
        </Card>
      </div>
    </AppShell>
  );
}
