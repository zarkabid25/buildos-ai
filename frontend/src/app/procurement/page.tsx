"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import { useMaterials, useWarehouses } from "@/lib/use-inventory";
import { useProjects } from "@/lib/use-projects";
import { useSuppliers } from "@/lib/use-suppliers";
import {
  useApprovePurchaseOrder,
  useCreateMaterialRequest,
  useCreatePurchaseOrder,
  useMaterialRequests,
  usePurchaseOrders,
  useReceiveGoods,
} from "@/lib/use-procurement";
import { formatCurrency } from "@/lib/utils";
import type { PurchaseOrder } from "@/lib/procurement-types";

const MR_STATUS_CLASSES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  converted: "bg-blue-100 text-blue-700",
};

const PO_STATUS_CLASSES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  pending_approval: "bg-amber-100 text-amber-700",
  approved: "bg-blue-100 text-blue-700",
  partially_received: "bg-purple-100 text-purple-700",
  received: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-700",
};

export default function ProcurementPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const { data: materialRequests } = useMaterialRequests();
  const { data: purchaseOrders } = usePurchaseOrders();
  const { data: projects } = useProjects();
  const { data: materials } = useMaterials();
  const { data: suppliers } = useSuppliers();
  const { data: warehouses } = useWarehouses();

  const createMR = useCreateMaterialRequest();
  const createPO = useCreatePurchaseOrder();
  const approvePO = useApprovePurchaseOrder();
  const receiveGoods = useReceiveGoods();

  const [mrForm, setMrForm] = useState({ project_id: "", material_id: "", quantity: "" });
  const [poForm, setPoForm] = useState({ supplier_id: "", project_id: "", material_id: "", quantity: "", rate: "" });
  const [receiveState, setReceiveState] = useState<Record<string, { warehouse_id: string; qty: string }>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  async function handleCreateMR() {
    setError(null);
    if (!mrForm.project_id || !mrForm.material_id || !mrForm.quantity) return;
    try {
      await createMR.mutateAsync({
        project_id: mrForm.project_id,
        items: [{ material_id: mrForm.material_id, quantity: mrForm.quantity }],
      });
      setMrForm({ project_id: "", material_id: "", quantity: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create material request");
    }
  }

  async function handleCreatePO() {
    setError(null);
    if (!poForm.supplier_id || !poForm.material_id || !poForm.quantity || !poForm.rate) return;
    try {
      await createPO.mutateAsync({
        supplier_id: poForm.supplier_id,
        project_id: poForm.project_id || undefined,
        items: [{ material_id: poForm.material_id, quantity: poForm.quantity, rate: poForm.rate }],
      });
      setPoForm({ supplier_id: "", project_id: "", material_id: "", quantity: "", rate: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create purchase order");
    }
  }

  async function handleReceive(po: PurchaseOrder) {
    setError(null);
    const state = receiveState[po.id];
    if (!state?.warehouse_id || !state?.qty) return;
    const item = po.items[0];
    try {
      await receiveGoods.mutateAsync({
        poId: po.id,
        warehouse_id: state.warehouse_id,
        items: [{ purchase_order_item_id: item.id, quantity_received: state.qty }],
      });
      setReceiveState((prev) => ({ ...prev, [po.id]: { warehouse_id: "", qty: "" } }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not record goods receipt");
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Procurement</h1>
          <p className="text-muted">Material Request → Purchase Order → Goods Receipt → Inventory</p>
        </div>

        {error && <p className="text-sm text-danger">{error}</p>}

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink">New material request</h2>
            <div className="space-y-2">
              <select
                className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
                value={mrForm.project_id}
                onChange={(e) => setMrForm({ ...mrForm, project_id: e.target.value })}
              >
                <option value="">Project...</option>
                {projects?.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <select
                className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
                value={mrForm.material_id}
                onChange={(e) => setMrForm({ ...mrForm, material_id: e.target.value })}
              >
                <option value="">Material...</option>
                {materials?.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
              <Input
                type="number"
                placeholder="Quantity"
                value={mrForm.quantity}
                onChange={(e) => setMrForm({ ...mrForm, quantity: e.target.value })}
              />
              <Button onClick={handleCreateMR} disabled={createMR.isPending} className="w-full">
                Submit request
              </Button>
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink">New purchase order</h2>
            <div className="space-y-2">
              <select
                className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
                value={poForm.supplier_id}
                onChange={(e) => setPoForm({ ...poForm, supplier_id: e.target.value })}
              >
                <option value="">Supplier...</option>
                {suppliers?.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <select
                className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
                value={poForm.material_id}
                onChange={(e) => setPoForm({ ...poForm, material_id: e.target.value })}
              >
                <option value="">Material...</option>
                {materials?.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  placeholder="Quantity"
                  value={poForm.quantity}
                  onChange={(e) => setPoForm({ ...poForm, quantity: e.target.value })}
                />
                <Input
                  type="number"
                  placeholder="Rate"
                  value={poForm.rate}
                  onChange={(e) => setPoForm({ ...poForm, rate: e.target.value })}
                />
              </div>
              <Button onClick={handleCreatePO} disabled={createPO.isPending} className="w-full">
                Create PO
              </Button>
            </div>
          </Card>
        </div>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink">Material Requests</h2>
          {(!materialRequests || materialRequests.length === 0) && (
            <p className="text-sm text-muted">No material requests yet.</p>
          )}
          <ul className="divide-y divide-border">
            {materialRequests?.map((mr) => (
              <li key={mr.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-ink">{mr.items.length} item(s)</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${MR_STATUS_CLASSES[mr.status]}`}>
                  {mr.status}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="overflow-x-auto p-0">
          <h2 className="px-4 pt-4 text-sm font-semibold text-ink">Purchase Orders</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-medium">PO #</th>
                <th className="px-4 py-3 font-medium">Total</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {(!purchaseOrders || purchaseOrders.length === 0) && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-sm text-muted">
                    No purchase orders yet.
                  </td>
                </tr>
              )}
              {purchaseOrders?.map((po) => (
                <tr key={po.id} className="border-b border-border last:border-0 align-top">
                  <td className="px-4 py-3 font-medium text-ink">{po.po_number}</td>
                  <td className="px-4 py-3 text-ink">{formatCurrency(po.total_amount)}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PO_STATUS_CLASSES[po.status]}`}>
                      {po.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {po.status === "pending_approval" && (
                      <Button
                        variant="secondary"
                        onClick={() => approvePO.mutate(po.id)}
                        disabled={approvePO.isPending}
                      >
                        Approve
                      </Button>
                    )}
                    {(po.status === "approved" || po.status === "partially_received") && (
                      <div className="flex flex-wrap items-center gap-2">
                        <select
                          className="h-8 rounded-md border border-border bg-surface px-2 text-xs"
                          value={receiveState[po.id]?.warehouse_id ?? ""}
                          onChange={(e) =>
                            setReceiveState((prev) => ({
                              ...prev,
                              [po.id]: { ...prev[po.id], warehouse_id: e.target.value, qty: prev[po.id]?.qty ?? "" },
                            }))
                          }
                        >
                          <option value="">Warehouse...</option>
                          {warehouses?.map((w) => (
                            <option key={w.id} value={w.id}>{w.name}</option>
                          ))}
                        </select>
                        <input
                          className="h-8 w-20 rounded-md border border-border bg-surface px-2 text-xs"
                          type="number"
                          placeholder="Qty"
                          value={receiveState[po.id]?.qty ?? ""}
                          onChange={(e) =>
                            setReceiveState((prev) => ({
                              ...prev,
                              [po.id]: { warehouse_id: prev[po.id]?.warehouse_id ?? "", qty: e.target.value },
                            }))
                          }
                        />
                        <Button onClick={() => handleReceive(po)} disabled={receiveGoods.isPending}>
                          Receive
                        </Button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </AppShell>
  );
}
