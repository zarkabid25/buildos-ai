"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import { useReplySupportTicket, useSupportTicket } from "@/lib/use-support";

const STATUS_CLASSES: Record<string, string> = {
  open: "bg-blue-50 text-primary",
  in_progress: "bg-amber-50 text-warning",
  waiting_on_requester: "bg-amber-50 text-warning",
  resolved: "bg-green-50 text-success",
  closed: "bg-gray-100 text-muted",
};

export default function SupportTicketDetailPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useFeedback();
  const { data: ticket, isLoading, isError, error, refetch } = useSupportTicket(params.id);
  const reply = useReplySupportTicket(params.id);
  const [body, setBody] = useState("");

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

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
    <AppShell>
      <div className="max-w-2xl space-y-4">
        {isLoading && <Skeleton className="h-64 w-full" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {ticket && (
          <>
            <Card className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h1 className="text-lg font-semibold text-ink">{ticket.subject}</h1>
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${STATUS_CLASSES[ticket.status]}`}>{ticket.status.replace(/_/g, " ")}</span>
              </div>
              <p className="text-sm text-muted capitalize">{ticket.category} &middot; {ticket.priority} priority</p>
            </Card>

            <Card className="space-y-3">
              <ul className="space-y-3">
                {ticket.messages.map((m) => (
                  <li key={m.id} className={`rounded-md border p-3 text-sm ${m.author_type === "staff" ? "border-primary/20 bg-blue-50" : "border-border bg-surface"}`}>
                    <p className="text-ink">{m.body}</p>
                    <p className="mt-1 text-xs text-muted">{m.author_type === "staff" ? "BuildOS Support" : m.author_name ?? "You"} &middot; {new Date(m.created_at).toLocaleString()}</p>
                  </li>
                ))}
              </ul>
              {ticket.status !== "closed" && (
                <div className="flex gap-2 border-t border-border pt-3">
                  <Input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write a reply..." className="flex-1" />
                  <Button onClick={handleReply} disabled={!body || reply.isPending}>{reply.isPending ? "Sending..." : "Send"}</Button>
                </div>
              )}
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}
