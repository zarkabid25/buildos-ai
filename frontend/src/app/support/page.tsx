"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import { useCreateSupportTicket, useSupportTickets } from "@/lib/use-support";
import type { SupportTicketCategory, SupportTicketPriority } from "@/lib/support-types";

const STATUS_CLASSES: Record<string, string> = {
  open: "bg-blue-50 text-primary",
  in_progress: "bg-amber-50 text-warning",
  waiting_on_requester: "bg-amber-50 text-warning",
  resolved: "bg-green-50 text-success",
  closed: "bg-gray-100 text-muted",
};

export default function SupportPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const { data, isLoading: listLoading, isError, error, refetch } = useSupportTickets();
  const createTicket = useCreateSupportTicket();
  const [showForm, setShowForm] = useState(false);
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState<SupportTicketCategory>("technical");
  const [priority, setPriority] = useState<SupportTicketPriority>("medium");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) return null;

  async function handleCreate() {
    try {
      await createTicket.mutateAsync({ subject, category, priority, message });
      setSubject("");
      setMessage("");
      setShowForm(false);
      toast("Support ticket created.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <AppShell>
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-ink">Support</h1>
            <p className="text-muted">Open a ticket, and our team will reply here.</p>
          </div>
          <Button onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "New ticket"}</Button>
        </div>

        {showForm && (
          <Card className="space-y-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <Label htmlFor="subject">Subject</Label>
                <Input id="subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="category">Category</Label>
                <select id="category" value={category} onChange={(e) => setCategory(e.target.value as SupportTicketCategory)} className="h-9 w-full rounded-md border border-border bg-surface px-3 text-sm">
                  <option value="technical">Technical</option>
                  <option value="billing">Billing</option>
                  <option value="account">Account</option>
                  <option value="marketplace">Marketplace</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>
            <div>
              <Label htmlFor="priority">Priority</Label>
              <select id="priority" value={priority} onChange={(e) => setPriority(e.target.value as SupportTicketPriority)} className="h-9 w-40 rounded-md border border-border bg-surface px-3 text-sm">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div>
              <Label htmlFor="message">Message</Label>
              <textarea id="message" value={message} onChange={(e) => setMessage(e.target.value)} rows={4} className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm" />
            </div>
            <Button onClick={handleCreate} disabled={!subject || !message || createTicket.isPending}>
              {createTicket.isPending ? "Creating..." : "Create ticket"}
            </Button>
          </Card>
        )}

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {listLoading && <TableSkeleton rows={3} />}
        {data && data.length === 0 && <EmptyState title="No support tickets yet" />}
        {data && data.length > 0 && (
          <div className="space-y-2">
            {data.map((t) => (
              <Link key={t.id} href={`/support/${t.id}`} className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-border bg-surface p-4 hover:border-primary/40">
                <div>
                  <p className="font-medium text-ink">{t.subject}</p>
                  <p className="text-sm text-muted capitalize">{t.category} &middot; {t.priority}</p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${STATUS_CLASSES[t.status]}`}>{t.status.replace(/_/g, " ")}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
