"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { SupplierShell } from "@/components/supplier-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/supplier-api";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSupplierPortalProduct, useUpdateSupplierPortalProduct } from "@/lib/use-supplier-portal";

export default function SupplierProductDetailPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useFeedback();
  const { data: product, isLoading, isError, error, refetch } = useSupplierPortalProduct(params.id);
  const updateProduct = useUpdateSupplierPortalProduct(params.id);

  const [form, setForm] = useState<{ name: string; category: string; unit: string; price: string; minimum_order_quantity: string; lead_time_days: string } | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  useEffect(() => {
    if (product && !form) {
      setForm({
        name: product.name, category: product.category ?? "", unit: product.unit, price: product.price,
        minimum_order_quantity: product.minimum_order_quantity, lead_time_days: product.lead_time_days != null ? String(product.lead_time_days) : "",
      });
    }
  }, [product, form]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  async function handleSave() {
    if (!form) return;
    try {
      await updateProduct.mutateAsync({
        name: form.name, category: form.category || undefined, unit: form.unit, price: form.price,
        minimum_order_quantity: form.minimum_order_quantity, lead_time_days: form.lead_time_days ? Number(form.lead_time_days) : undefined,
      });
      toast("Product updated.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleToggleActive() {
    if (!product) return;
    try {
      await updateProduct.mutateAsync({ is_active: !product.is_active });
      toast(product.is_active ? "Product deactivated." : "Product activated.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <SupplierShell breadcrumb="Products">
      <div className="max-w-xl">
        {isLoading && <Skeleton className="h-64 w-full" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {product && form && (
          <Card className="space-y-4">
            <div className="flex items-center justify-between">
              <h1 className="text-lg font-semibold text-gray-900">{product.name}</h1>
              <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${product.is_active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                {product.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            <div>
              <Label htmlFor="name">Name</Label>
              <Input id="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="category">Category</Label>
                <Input id="category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="unit">Unit</Label>
                <Input id="unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label htmlFor="price">Price</Label>
                <Input id="price" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="moq">Min. order qty</Label>
                <Input id="moq" value={form.minimum_order_quantity} onChange={(e) => setForm({ ...form, minimum_order_quantity: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="lead">Lead time (days)</Label>
                <Input id="lead" type="number" value={form.lead_time_days} onChange={(e) => setForm({ ...form, lead_time_days: e.target.value })} />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleSave} disabled={updateProduct.isPending}>
                {updateProduct.isPending ? "Saving..." : "Save changes"}
              </Button>
              <Button variant="secondary" onClick={handleToggleActive} disabled={updateProduct.isPending}>
                {product.is_active ? "Deactivate" : "Activate"}
              </Button>
            </div>
          </Card>
        )}
      </div>
    </SupplierShell>
  );
}
