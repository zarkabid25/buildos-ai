"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { SupplierShell } from "@/components/supplier-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/supplier-api";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useCreateSupplierSupportTicket, useSupplierSupportTickets } from "@/lib/use-supplier-portal";

const STATUS_CLASSES: Record<string, string> = {
  open: "bg-blue-50 text-blue-700",
  in_progress: "bg-amber-50 text-amber-700",
  waiting_on_requester: "bg-amber-50 text-amber-700",
  resolved: "bg-green-50 text-green-700",
  closed: "bg-gray-100 text-gray-500",
};

export default function SupplierSupportPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const { data, isLoading, isError, error, refetch } = useSupplierSupportTickets();
  const createTicket = useCreateSupplierSupportTicket();
  const [showForm, setShowForm] = useState(false);
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState("technical");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  async function handleCreate() {
    try {
      await createTicket.mutateAsync({ subject, category, message });
      setSubject("");
      setMessage("");
      setShowForm(false);
      toast("Support ticket created.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <SupplierShell breadcrumb="Support">
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Support</h1>
            <p className="mt-1 text-sm text-gray-500">Open a ticket, and BuildOS staff will reply here.</p>
          </div>
          <Button className="h-11" onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "New ticket"}</Button>
        </div>

        {showForm && (
          <Card className="space-y-3">
            <div>
              <Label htmlFor="subject">Subject</Label>
              <Input id="subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="category">Category</Label>
              <select id="category" value={category} onChange={(e) => setCategory(e.target.value)} className="h-10 w-48 rounded-md border border-gray-300 px-3 text-sm">
                <option value="technical">Technical</option>
                <option value="billing">Billing</option>
                <option value="account">Account</option>
                <option value="marketplace">Marketplace</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <Label htmlFor="message">Message</Label>
              <textarea id="message" value={message} onChange={(e) => setMessage(e.target.value)} rows={4} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <Button onClick={handleCreate} disabled={!subject || !message || createTicket.isPending}>
              {createTicket.isPending ? "Creating..." : "Create ticket"}
            </Button>
          </Card>
        )}

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {isLoading && <TableSkeleton rows={3} />}
        {data && data.length === 0 && <EmptyState title="No support tickets yet" />}
        {data && data.length > 0 && (
          <div className="space-y-2">
            {data.map((t) => (
              <Link key={t.id} href={`/supplier-portal/support/${t.id}`} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-gray-200 bg-white p-4 hover:border-blue-300">
                <div>
                  <p className="font-medium text-gray-900">{t.subject}</p>
                  <p className="text-sm capitalize text-gray-500">{t.category} &middot; {t.priority}</p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${STATUS_CLASSES[t.status]}`}>{t.status.replace(/_/g, " ")}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </SupplierShell>
  );
}
