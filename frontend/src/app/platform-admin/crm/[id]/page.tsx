"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { AiNarrationPanel } from "@/components/ai-narration-panel";
import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState } from "@/components/ui/states";
import { ApiError, platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useAddCrmActivity, useAddCrmContact, useConvertCrmOrganization, useCrmOrganization } from "@/lib/use-crm";

const contactSchema = z.object({
  name: z.string().trim().min(1, "Name is required"),
  title: z.string().trim().optional(),
  email: z.string().trim().email("Enter a valid email").optional().or(z.literal("")),
  phone: z.string().trim().optional(),
});
type ContactInput = z.infer<typeof contactSchema>;

const activitySchema = z.object({
  type: z.enum(["call", "meeting", "note", "task"]),
  summary: z.string().trim().min(1, "Required"),
  due_at: z.string().optional(),
});
type ActivityInput = z.infer<typeof activitySchema>;

export default function CrmOrganizationDetailPage() {
  const { admin, accessToken, isLoading } = usePlatformAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast, confirm } = useFeedback();
  const isReadOnly = admin?.role === "support";

  const { data: org, isLoading: orgLoading, isError, error, refetch } = useCrmOrganization(params.id);
  const addContact = useAddCrmContact();
  const addActivity = useAddCrmActivity();
  const convertOrg = useConvertCrmOrganization();
  const [convertMode, setConvertMode] = useState<"create" | "link" | null>(null);
  const [companyCode, setCompanyCode] = useState("");
  const [existingCompanyId, setExistingCompanyId] = useState("");

  const contactForm = useForm<ContactInput>({ resolver: zodResolver(contactSchema) });
  const activityForm = useForm<ActivityInput>({
    resolver: zodResolver(activitySchema),
    defaultValues: { type: "note" },
  });

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function onAddContact(values: ContactInput) {
    if (!org) return;
    try {
      await addContact.mutateAsync({ orgId: org.id, ...values, email: values.email || undefined });
      contactForm.reset();
      toast("Contact added.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function onAddActivity(values: ActivityInput) {
    if (!org) return;
    try {
      await addActivity.mutateAsync({
        orgId: org.id,
        type: values.type,
        summary: values.summary,
        due_at: values.due_at ? new Date(values.due_at).toISOString() : undefined,
      });
      activityForm.reset({ type: "note", summary: "", due_at: "" });
      toast("Activity logged.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleConvertCreate() {
    if (!org) return;
    const ok = await confirm({
      title: `Convert ${org.name} to a company?`,
      body: "This creates a new BuildOS company (pending platform approval).",
      confirmLabel: "Convert",
    });
    if (!ok) return;
    try {
      await convertOrg.mutateAsync({ orgId: org.id, create_company_name: org.name, create_company_code: companyCode });
      toast("Converted. The new company is pending approval.", "success");
      setConvertMode(null);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleConvertLink() {
    if (!org) return;
    try {
      await convertOrg.mutateAsync({ orgId: org.id, link_existing_company_id: existingCompanyId });
      toast("Linked to the existing company.", "success");
      setConvertMode(null);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb={org ? org.name : "CRM"}>
      <div className="max-w-3xl space-y-5">
        {orgLoading && <div className="h-32 animate-pulse rounded-[14px] bg-[var(--bo-nav-active)]" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {org && (
          <>
            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h1 className="text-2xl font-semibold tracking-[-0.025em] text-[var(--bo-text)]">{org.name}</h1>
                  <p className="mt-1 text-sm text-[var(--bo-text-muted)]">
                    {org.pipeline_type === "saas_sales" ? "SaaS Sales" : "Supplier Acquisition"} &middot; stage:{" "}
                    {org.stage} &middot; owner: {org.owner_staff_name ?? "Unassigned"}
                  </p>
                </div>
                {!isReadOnly && !org.converted_company_id && (
                  <div className="flex gap-2">
                    <Button variant="secondary" onClick={() => setConvertMode(convertMode === "link" ? null : "link")}>
                      Link existing company
                    </Button>
                    <Button onClick={() => setConvertMode(convertMode === "create" ? null : "create")}>
                      Convert to company
                    </Button>
                  </div>
                )}
                {org.converted_company_id && (
                  <span className="rounded-full bg-[var(--bo-success-bg)] px-3 py-1 text-xs font-medium text-[var(--bo-success)]">
                    Converted
                  </span>
                )}
              </div>

              <AiNarrationPanel
                label="Ask AI for a lead summary and next steps"
                theme="dark"
                onGenerate={() => platformApi.post<{ narration: string }>(`/platform/ai/crm-organizations/${org.id}/insights`, {}, accessToken ?? undefined)}
              />

              {convertMode === "create" && (
                <div className="mt-4 flex items-end gap-2 border-t border-[var(--bo-divider)] pt-4">
                  <div>
                    <Label htmlFor="code">New company code</Label>
                    <Input id="code" value={companyCode} onChange={(e) => setCompanyCode(e.target.value)} />
                  </div>
                  <Button onClick={handleConvertCreate} disabled={!companyCode || convertOrg.isPending}>
                    Confirm
                  </Button>
                </div>
              )}
              {convertMode === "link" && (
                <div className="mt-4 flex items-end gap-2 border-t border-[var(--bo-divider)] pt-4">
                  <div>
                    <Label htmlFor="existing">Existing company ID</Label>
                    <Input id="existing" value={existingCompanyId} onChange={(e) => setExistingCompanyId(e.target.value)} />
                  </div>
                  <Button onClick={handleConvertLink} disabled={!existingCompanyId || convertOrg.isPending}>
                    Confirm
                  </Button>
                </div>
              )}
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Contacts</h2>
              {org.contacts.length === 0 && <p className="mt-2 text-sm text-[var(--bo-text-muted)]">No contacts yet.</p>}
              <ul className="mt-2 divide-y divide-[var(--bo-divider)]">
                {org.contacts.map((c) => (
                  <li key={c.id} className="py-2 text-sm">
                    <span className="font-medium text-[var(--bo-text)]">{c.name}</span>
                    {c.title && <span className="text-[var(--bo-text-muted)]"> &middot; {c.title}</span>}
                    {c.email && <span className="text-[var(--bo-text-muted)]"> &middot; {c.email}</span>}
                  </li>
                ))}
              </ul>
              {!isReadOnly && (
                <form onSubmit={contactForm.handleSubmit(onAddContact)} className="mt-4 grid gap-3 sm:grid-cols-4">
                  <Input placeholder="Name" {...contactForm.register("name")} />
                  <Input placeholder="Title" {...contactForm.register("title")} />
                  <Input placeholder="Email" {...contactForm.register("email")} />
                  <Button type="submit" variant="secondary" disabled={contactForm.formState.isSubmitting}>
                    Add contact
                  </Button>
                </form>
              )}
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Activity</h2>
              <form onSubmit={activityForm.handleSubmit(onAddActivity)} className="mt-3 grid gap-3 sm:grid-cols-4">
                <select
                  {...activityForm.register("type")}
                  className="h-10 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm"
                >
                  <option value="note">Note</option>
                  <option value="call">Call</option>
                  <option value="meeting">Meeting</option>
                  <option value="task">Follow-up / Reminder</option>
                </select>
                <Input placeholder="Summary" className="sm:col-span-2" {...activityForm.register("summary")} />
                <Input type="datetime-local" {...activityForm.register("due_at")} />
                <Button type="submit" className="sm:col-span-4 sm:w-fit" disabled={activityForm.formState.isSubmitting}>
                  Log activity
                </Button>
              </form>

              <ul className="mt-4 divide-y divide-[var(--bo-divider)]">
                {org.activities.map((a) => (
                  <li key={a.id} className="py-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="font-medium capitalize text-[var(--bo-text)]">{a.type}</span>
                      <span className="text-xs text-[var(--bo-text-muted)]">
                        {new Date(a.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[var(--bo-text-secondary)]">{a.summary}</p>
                    {a.due_at && (
                      <p className="mt-0.5 text-xs text-[var(--bo-text-muted)]">
                        Due {new Date(a.due_at).toLocaleString()} {a.completed_at ? "(done)" : ""}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </PlatformShell>
  );
}
