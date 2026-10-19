"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { SupplierShell } from "@/components/supplier-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/supplier-api";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useCreateSupplierPortalProduct } from "@/lib/use-supplier-portal";

export default function NewSupplierProductPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const createProduct = useCreateSupplierPortalProduct();

  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("");
  const [price, setPrice] = useState("");
  const [moq, setMoq] = useState("1");
  const [leadTime, setLeadTime] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createProduct.mutateAsync({
        name, category: category || undefined, unit, price,
        minimum_order_quantity: moq || undefined,
        lead_time_days: leadTime ? Number(leadTime) : undefined,
      });
      toast("Product added.", "success");
      router.push("/supplier-portal/products");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <SupplierShell breadcrumb="Products">
      <div className="max-w-xl">
        <h1 className="text-2xl font-semibold text-gray-900">Add a product</h1>
        <Card className="mt-4 space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="category">Category</Label>
                <Input id="category" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. cement" />
              </div>
              <div>
                <Label htmlFor="unit">Unit</Label>
                <Input id="unit" required value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="bag, ton, kg..." />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label htmlFor="price">Price</Label>
                <Input id="price" required value={price} onChange={(e) => setPrice(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="moq">Min. order qty</Label>
                <Input id="moq" value={moq} onChange={(e) => setMoq(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="lead">Lead time (days)</Label>
                <Input id="lead" type="number" value={leadTime} onChange={(e) => setLeadTime(e.target.value)} />
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="submit" className="h-11" disabled={createProduct.isPending}>
                {createProduct.isPending ? "Adding..." : "Add product"}
              </Button>
              <Button type="button" variant="secondary" className="h-11" onClick={() => router.push("/supplier-portal/products")}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </SupplierShell>
  );
}
