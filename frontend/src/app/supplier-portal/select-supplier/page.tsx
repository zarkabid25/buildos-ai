"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/supplier-api";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSupplierSelectSupplier } from "@/lib/use-supplier-portal";

export default function SelectSupplierPage() {
  const router = useRouter();
  const { toast } = useFeedback();
  const { memberships, refreshToken, setActiveSupplier, isLoading } = useSupplierAuth();
  const selectSupplier = useSupplierSelectSupplier();

  useEffect(() => {
    if (!isLoading && !refreshToken) router.replace("/supplier-portal/login");
  }, [isLoading, refreshToken, router]);

  async function handleSelect(marketplaceSupplierId: string) {
    if (!refreshToken) return;
    try {
      const result = await selectSupplier.mutateAsync({ refresh_token: refreshToken, marketplace_supplier_id: marketplaceSupplierId });
      setActiveSupplier(result);
      router.push("/supplier-portal");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  if (isLoading || !refreshToken) return null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-sm space-y-4">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Choose a supplier organization</h1>
          <p className="mt-1 text-sm text-gray-500">Your account belongs to more than one -- pick which to work in.</p>
        </div>
        <div className="space-y-2">
          {memberships.map((m) => (
            <button
              key={m.marketplace_supplier_id}
              onClick={() => handleSelect(m.marketplace_supplier_id)}
              disabled={selectSupplier.isPending || m.status !== "active"}
              className="flex h-14 w-full items-center justify-between rounded-lg border border-gray-200 px-4 text-left hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <div>
                <p className="font-medium text-gray-900">{m.marketplace_supplier_name}</p>
                <p className="text-xs capitalize text-gray-500">{m.role}</p>
              </div>
              {m.status !== "active" && <span className="text-xs text-red-500">{m.status}</span>}
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}
