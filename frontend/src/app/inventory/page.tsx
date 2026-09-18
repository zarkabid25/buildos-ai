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
import {
  useCreateMaterial,
  useCreateWarehouse,
  useInventoryDashboard,
  useMaterials,
  useStockIn,
  useStockLevels,
  useStockOut,
  useWarehouses,
} from "@/lib/use-inventory";

export default function InventoryPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const { data: dashboard } = useInventoryDashboard();
  const { data: stockLevels } = useStockLevels();
  const { data: materials } = useMaterials();
  const { data: warehouses } = useWarehouses();

  const createMaterial = useCreateMaterial();
  const createWarehouse = useCreateWarehouse();
  const stockIn = useStockIn();
  const stockOut = useStockOut();

  const [materialForm, setMaterialForm] = useState({ name: "", sku: "", unit: "", reorder_point: "" });
  const [warehouseForm, setWarehouseForm] = useState({ name: "", location: "" });
  const [moveForm, setMoveForm] = useState({ material_id: "", warehouse_id: "", quantity: "" });
  const [moveError, setMoveError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  async function handleAddMaterial() {
    if (!materialForm.name || !materialForm.sku || !materialForm.unit) return;
    await createMaterial.mutateAsync({
      name: materialForm.name,
      sku: materialForm.sku,
      unit: materialForm.unit,
      reorder_point: materialForm.reorder_point ? Number(materialForm.reorder_point) : 0,
    });
    setMaterialForm({ name: "", sku: "", unit: "", reorder_point: "" });
  }

  async function handleAddWarehouse() {
    if (!warehouseForm.name) return;
    await createWarehouse.mutateAsync(warehouseForm);
    setWarehouseForm({ name: "", location: "" });
  }

  async function handleStockIn() {
    setMoveError(null);
    if (!moveForm.material_id || !moveForm.warehouse_id || !moveForm.quantity) return;
    try {
      await stockIn.mutateAsync(moveForm);
      setMoveForm({ material_id: "", warehouse_id: "", quantity: "" });
    } catch (err) {
      setMoveError(err instanceof ApiError ? err.message : "Stock in failed");
    }
  }

  async function handleStockOut() {
    setMoveError(null);
    if (!moveForm.material_id || !moveForm.warehouse_id || !moveForm.quantity) return;
    try {
      await stockOut.mutateAsync(moveForm);
      setMoveForm({ material_id: "", warehouse_id: "", quantity: "" });
    } catch (err) {
      setMoveError(err instanceof ApiError ? err.message : "Stock out failed");
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Inventory</h1>
          <p className="text-muted">Materials, warehouses and stock across your company.</p>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Card>
            <div className="text-2xl font-semibold text-ink">{dashboard?.total_materials ?? "—"}</div>
            <div className="text-sm text-muted">Total Materials</div>
          </Card>
          <Card>
            <div className="text-2xl font-semibold text-warning">{dashboard?.low_stock_count ?? "—"}</div>
            <div className="text-sm text-muted">Low Stock</div>
          </Card>
          <Card>
            <div className="text-2xl font-semibold text-danger">{dashboard?.out_of_stock_count ?? "—"}</div>
            <div className="text-sm text-muted">Out of Stock</div>
          </Card>
          <Card>
            <div className="text-2xl font-semibold text-ink">{dashboard?.warehouse_count ?? "—"}</div>
            <div className="text-sm text-muted">Warehouses</div>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink">Add material</h2>
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Name" value={materialForm.name} onChange={(e) => setMaterialForm({ ...materialForm, name: e.target.value })} />
              <Input placeholder="SKU" value={materialForm.sku} onChange={(e) => setMaterialForm({ ...materialForm, sku: e.target.value })} />
              <Input placeholder="Unit (e.g. Bag)" value={materialForm.unit} onChange={(e) => setMaterialForm({ ...materialForm, unit: e.target.value })} />
              <Input placeholder="Reorder point" type="number" value={materialForm.reorder_point} onChange={(e) => setMaterialForm({ ...materialForm, reorder_point: e.target.value })} />
            </div>
            <Button className="mt-3" onClick={handleAddMaterial} disabled={createMaterial.isPending}>
              Add material
            </Button>
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink">Add warehouse</h2>
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Name" value={warehouseForm.name} onChange={(e) => setWarehouseForm({ ...warehouseForm, name: e.target.value })} />
              <Input placeholder="Location" value={warehouseForm.location} onChange={(e) => setWarehouseForm({ ...warehouseForm, location: e.target.value })} />
            </div>
            <Button className="mt-3" onClick={handleAddWarehouse} disabled={createWarehouse.isPending}>
              Add warehouse
            </Button>
          </Card>
        </div>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink">Stock In / Stock Out</h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div>
              <Label>Material</Label>
              <select
                className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
                value={moveForm.material_id}
                onChange={(e) => setMoveForm({ ...moveForm, material_id: e.target.value })}
              >
                <option value="">Select...</option>
                {materials?.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Warehouse</Label>
              <select
                className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
                value={moveForm.warehouse_id}
                onChange={(e) => setMoveForm({ ...moveForm, warehouse_id: e.target.value })}
              >
                <option value="">Select...</option>
                {warehouses?.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Quantity</Label>
              <Input type="number" value={moveForm.quantity} onChange={(e) => setMoveForm({ ...moveForm, quantity: e.target.value })} />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={handleStockIn} disabled={stockIn.isPending} className="w-full">
                Stock In
              </Button>
              <Button onClick={handleStockOut} disabled={stockOut.isPending} variant="secondary" className="w-full">
                Stock Out
              </Button>
            </div>
          </div>
          {moveError && <p className="mt-2 text-sm text-danger">{moveError}</p>}
        </Card>

        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-medium">Material</th>
                <th className="px-4 py-3 font-medium">Warehouse</th>
                <th className="px-4 py-3 font-medium">On Hand</th>
              </tr>
            </thead>
            <tbody>
              {(!stockLevels || stockLevels.length === 0) && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-sm text-muted">
                    No stock movements yet. Add a material and warehouse, then use Stock In above.
                  </td>
                </tr>
              )}
              {stockLevels?.map((level) => (
                <tr key={`${level.material_id}-${level.warehouse_id}`} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 text-ink">{level.material_name}</td>
                  <td className="px-4 py-3 text-muted">{level.warehouse_name}</td>
                  <td className="px-4 py-3 text-ink">
                    {level.quantity_on_hand} {level.unit}
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
