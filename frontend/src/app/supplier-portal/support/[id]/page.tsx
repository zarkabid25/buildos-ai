"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { SupplierShell } from "@/components/supplier-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/supplier-api";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useReplySupplierSupportTicket, useSupplierSupportTicket } from "@/lib/use-supplier-portal";

const STATUS_CLASSES: Record<string, string> = {
  open: "bg-blue-50 text-blue-700",
  in_progress: "bg-amber-50 text-amber-700",
  waiting_on_requester: "bg-amber-50 text-amber-700",
  resolved: "bg-green-50 text-green-700",
  closed: "bg-gray-100 text-gray-500",
};

export default function SupplierSupportTicketDetailPage() {
  const { refreshToken, activeSupplierId, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useFeedback();
  const { data: ticket, isLoading, isError, error, refetch } = useSupplierSupportTicket(params.id);
  const reply = useReplySupplierSupportTicket(params.id);
  const [body, setBody] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  async function handleReply() {
    try {
      await reply.mutateAsync(body);
      setBody("");
      toast("Reply sent.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <SupplierShell breadcrumb="Support">
      <div className="max-w-2xl space-y-4">
        {isLoading && <Skeleton className="h-64 w-full" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {ticket && (
          <>
            <Card className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h1 className="text-lg font-semibold text-gray-900">{ticket.subject}</h1>
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${STATUS_CLASSES[ticket.status]}`}>{ticket.status.replace(/_/g, " ")}</span>
              </div>
              <p className="text-sm capitalize text-gray-500">{ticket.category} &middot; {ticket.priority} priority</p>
            </Card>

            <Card className="space-y-3">
              <ul className="space-y-3">
                {ticket.messages.map((m) => (
                  <li key={m.id} className={`rounded-md border p-3 text-sm ${m.author_type === "staff" ? "border-blue-200 bg-blue-50" : "border-gray-200 bg-white"}`}>
                    <p className="text-gray-900">{m.body}</p>
                    <p className="mt-1 text-xs text-gray-400">{m.author_type === "staff" ? "BuildOS Support" : m.author_name ?? "You"} &middot; {new Date(m.created_at).toLocaleString()}</p>
                  </li>
                ))}
              </ul>
              {ticket.status !== "closed" && (
                <div className="flex gap-2 border-t border-gray-100 pt-3">
                  <Input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write a reply..." className="flex-1" />
                  <Button onClick={handleReply} disabled={!body || reply.isPending}>{reply.isPending ? "Sending..." : "Send"}</Button>
                </div>
              )}
            </Card>
          </>
        )}
      </div>
    </SupplierShell>
  );
}
