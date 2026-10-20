"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { AiNarrationPanel } from "@/components/ai-narration-panel";
import { AppShell } from "@/components/app-shell";
import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useConnectSupplier, useDiscoverSupplierDetail } from "@/lib/use-marketplace-discovery";

export default function MarketplaceSupplierPage() {
  const { user, isLoading: authLoading, accessToken } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useFeedback();
  const [connecting, setConnecting] = useState(false);

  const { data: supplier, isLoading, isError, error, refetch } = useDiscoverSupplierDetail(params.id);
  const connect = useConnectSupplier();

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  async function handleConnect() {
    if (!supplier) return;
    setConnecting(true);
    try {
      await connect.mutateAsync({ supplierId: supplier.id, create_new_erp_supplier: true });
      toast(`Connected to ${supplier.name}. A matching supplier record was created in your Suppliers list.`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <AppShell>
      <div className="max-w-2xl space-y-6">
        {isLoading && (
          <Card>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="mt-4 h-4 w-full" />
          </Card>
        )}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {supplier && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold text-ink">{supplier.name}</h1>
                <p className="text-muted">{supplier.categories.join(", ") || "No categories listed"}</p>
              </div>
              {!supplier.is_connected ? (
                <Button onClick={handleConnect} disabled={connecting}>
                  {connecting ? "Connecting..." : "Request quotation / Connect"}
                </Button>
              ) : (
                <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary">Connected</span>
              )}
            </div>

            <AiNarrationPanel
              label="Ask AI why this supplier might be a good fit"
              onGenerate={() => api.get<{ narration: string }>(`/marketplace/suppliers/${supplier.id}/ai/recommendation`, accessToken ?? undefined)}
            />

            <Card>
              <h2 className="font-medium text-ink">Delivery coverage</h2>
              <p className="mt-1 text-sm text-muted">{supplier.coverage_areas.join(", ") || "Not specified"}</p>
            </Card>

            <Card>
              <h2 className="font-medium text-ink">Product catalog</h2>
              {supplier.products.length === 0 && <p className="mt-2 text-sm text-muted">No products listed yet.</p>}
              {supplier.products.length > 0 && (
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-muted">
                      <tr>
                        <th className="py-2 pr-4">Product</th>
                        <th className="py-2 pr-4">Price</th>
                        <th className="py-2 pr-4">Min. qty</th>
                        <th className="py-2 pr-4">Lead time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {supplier.products.map((p) => (
                        <tr key={p.id} className="border-t border-border">
                          <td className="py-2 pr-4 font-medium text-ink">{p.name}</td>
                          <td className="py-2 pr-4">{p.price}/{p.unit}</td>
                          <td className="py-2 pr-4">{p.minimum_order_quantity} {p.unit}</td>
                          <td className="py-2 pr-4">{p.lead_time_days != null ? `${p.lead_time_days} days` : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {supplier.is_connected && (
              <Card>
                <p className="text-sm text-muted">
                  This supplier is connected. A matching entry now exists in your{" "}
                  <a href="/suppliers" className="font-medium text-primary">
                    Suppliers
                  </a>{" "}
                  list, so you can invite them to any RFQ the same way as any other supplier.
                </p>
              </Card>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
