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
import { useDeclineRfqInvitation, useSubmitSupplierQuotation, useSupplierRfqDetail } from "@/lib/use-supplier-portal";

export default function SupplierRfqDetailPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast, confirm } = useFeedback();
  const { data: rfq, isLoading, isError, error, refetch } = useSupplierRfqDetail(params.id);
  const submitQuotation = useSubmitSupplierQuotation(params.id);
  const declineInvitation = useDeclineRfqInvitation(params.id);

  const [rates, setRates] = useState<Record<string, string>>({});
  const [deliveryDays, setDeliveryDays] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  useEffect(() => {
    if (rfq?.my_quotation) {
      const r: Record<string, string> = {};
      for (const item of rfq.my_quotation.items) r[item.rfq_item_id] = item.rate;
      setRates(r);
      setDeliveryDays(rfq.my_quotation.delivery_days != null ? String(rfq.my_quotation.delivery_days) : "");
      setValidUntil(rfq.my_quotation.valid_until ?? "");
      setNotes(rfq.my_quotation.notes ?? "");
    }
  }, [rfq]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  async function handleSubmit() {
    if (!rfq) return;
    const items = rfq.items.map((i) => ({ rfq_item_id: i.id, rate: rates[i.id] }));
    if (items.some((i) => !i.rate)) {
      toast("Enter a rate for every item.", "error");
      return;
    }
    try {
      await submitQuotation.mutateAsync({
        items, delivery_days: deliveryDays ? Number(deliveryDays) : undefined, valid_until: validUntil || undefined, notes: notes || undefined,
      });
      toast(rfq.my_quotation ? "Quotation revised." : "Quotation submitted.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleDecline() {
    const ok = await confirm({ title: "Decline this RFQ?", body: "You won't be able to submit a quotation for it afterwards.", confirmLabel: "Decline", danger: true });
    if (!ok) return;
    try {
      await declineInvitation.mutateAsync();
      toast("Invitation declined.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <SupplierShell breadcrumb="RFQs">
      <div className="max-w-2xl space-y-5">
        {isLoading && <Skeleton className="h-64 w-full" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {rfq && (
          <>
            <Card className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h1 className="text-lg font-semibold text-gray-900">{rfq.title}</h1>
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium capitalize text-gray-700">{rfq.invitation_status}</span>
              </div>
              <p className="text-sm text-gray-500">{rfq.rfq_number} &middot; {rfq.company_name}</p>
              {rfq.response_due && <p className="text-sm text-gray-500">Response due {rfq.response_due}</p>}
              {rfq.notes && <p className="text-sm text-gray-600">{rfq.notes}</p>}
            </Card>

            <Card className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-900">Materials requested</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
                    <th className="py-2">Material</th>
                    <th className="py-2">Quantity</th>
                    <th className="py-2">Your rate</th>
                  </tr>
                </thead>
                <tbody>
                  {rfq.items.map((item) => (
                    <tr key={item.id} className="border-b border-gray-100 last:border-0">
                      <td className="py-2 text-gray-900">{item.material_name}</td>
                      <td className="py-2 text-gray-600">{item.quantity} {item.unit}</td>
                      <td className="py-2">
                        <Input
                          className="h-9 w-28"
                          value={rates[item.id] ?? ""}
                          onChange={(e) => setRates({ ...rates, [item.id]: e.target.value })}
                          disabled={rfq.invitation_status === "declined"}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {rfq.invitation_status !== "declined" && (
                <div className="grid grid-cols-2 gap-3 border-t border-gray-100 pt-3">
                  <div>
                    <Label htmlFor="delivery">Delivery days</Label>
                    <Input id="delivery" type="number" value={deliveryDays} onChange={(e) => setDeliveryDays(e.target.value)} />
                  </div>
                  <div>
                    <Label htmlFor="valid">Valid until</Label>
                    <Input id="valid" type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} />
                  </div>
                  <div className="col-span-2">
                    <Label htmlFor="notes">Notes</Label>
                    <Input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
                  </div>
                </div>
              )}

              {rfq.invitation_status !== "declined" && (
                <div className="flex gap-2">
                  <Button onClick={handleSubmit} className="h-11" disabled={submitQuotation.isPending}>
                    {submitQuotation.isPending ? "Submitting..." : rfq.my_quotation ? "Revise quotation" : "Submit quotation"}
                  </Button>
                  {!rfq.my_quotation && rfq.invitation_status === "invited" && (
                    <Button variant="secondary" className="h-11" onClick={handleDecline} disabled={declineInvitation.isPending}>
                      Decline
                    </Button>
                  )}
                </div>
              )}

              {rfq.my_quotation && (
                <p className="text-sm text-gray-500">Current total: <span className="font-medium text-gray-900">{rfq.my_quotation.total}</span></p>
              )}
            </Card>
          </>
        )}
      </div>
    </SupplierShell>
  );
}
