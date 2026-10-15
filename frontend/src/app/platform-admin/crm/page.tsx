"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { CRM_STAGES, type CrmOrganization, type CrmPipelineType, type CrmStage } from "@/lib/crm-types";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useCreateCrmOrganization, useCrmOrganizations, useUpdateCrmOrganization } from "@/lib/use-crm";
import { cn } from "@/lib/utils";

const STAGE_LABELS: Record<CrmStage, string> = {
  new: "New",
  contacted: "Contacted",
  qualified: "Qualified",
  proposal: "Proposal",
  negotiation: "Negotiation",
  won: "Won",
  lost: "Lost",
};

const PIPELINE_LABELS: Record<CrmPipelineType, string> = {
  saas_sales: "SaaS Sales",
  supplier_acquisition: "Supplier Acquisition",
};

const createSchema = z.object({
  name: z.string().trim().min(1, "Name is required"),
  source: z.string().trim().optional(),
  email: z.string().trim().email("Enter a valid email").optional().or(z.literal("")),
});
type CreateInput = z.infer<typeof createSchema>;

function OrgCard({ org }: { org: CrmOrganization }) {
  const updateOrg = useUpdateCrmOrganization();
  return (
    <div className="rounded-lg border border-[var(--bo-border)] bg-[var(--bo-surface)] p-3 shadow-[var(--bo-shadow-card)]">
      <Link href={`/platform-admin/crm/${org.id}`} className="text-sm font-medium text-[var(--bo-primary)]">
        {org.name}
      </Link>
      <p className="mt-0.5 text-xs text-[var(--bo-text-muted)]">{org.owner_staff_name ?? "Unassigned"}</p>
      <select
        value={org.stage}
        onChange={(e) => updateOrg.mutate({ id: org.id, stage: e.target.value as CrmStage })}
        className="mt-2 h-8 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-2 text-xs text-[var(--bo-text)]"
      >
        {CRM_STAGES.map((s) => (
          <option key={s} value={s}>
            {STAGE_LABELS[s]}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function PlatformCrmPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const [pipeline, setPipeline] = useState<CrmPipelineType>("saas_sales");
  const [view, setView] = useState<"kanban" | "list">("kanban");
  const [showForm, setShowForm] = useState(false);

  const { data, isLoading: listLoading, isError, error, refetch } = useCrmOrganizations(pipeline);
  const createOrg = useCreateCrmOrganization();
  const isReadOnly = admin?.role === "support";

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateInput>({ resolver: zodResolver(createSchema) });

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function onCreate(values: CreateInput) {
    try {
      await createOrg.mutateAsync({
        name: values.name,
        pipeline_type: pipeline,
        source: values.source || undefined,
        email: values.email || undefined,
      });
      reset();
      setShowForm(false);
      toast("Lead added.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="CRM">
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] p-1">
            {(["saas_sales", "supplier_acquisition"] as CrmPipelineType[]).map((p) => (
              <button
                key={p}
                onClick={() => setPipeline(p)}
                className={cn(
                  "rounded px-3 py-1.5 text-sm font-medium",
                  pipeline === p ? "bg-[var(--bo-nav-active)] text-[var(--bo-text)]" : "text-[var(--bo-text-muted)]"
                )}
              >
                {PIPELINE_LABELS[p]}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] p-1">
              <button
                onClick={() => setView("kanban")}
                className={cn("rounded px-3 py-1.5 text-sm", view === "kanban" ? "bg-[var(--bo-nav-active)]" : "text-[var(--bo-text-muted)]")}
              >
                Kanban
              </button>
              <button
                onClick={() => setView("list")}
                className={cn("rounded px-3 py-1.5 text-sm", view === "list" ? "bg-[var(--bo-nav-active)]" : "text-[var(--bo-text-muted)]")}
              >
                List
              </button>
            </div>
            {!isReadOnly && <Button onClick={() => setShowForm((s) => !s)}>Add lead</Button>}
          </div>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit(onCreate)}
            className="grid gap-4 rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)] sm:grid-cols-4"
          >
            <div>
              <Label htmlFor="name">Name</Label>
              <Input id="name" {...register("name")} />
              {errors.name && <p className="mt-1 text-xs text-danger">{errors.name.message}</p>}
            </div>
            <div>
              <Label htmlFor="source">Source</Label>
              <Input id="source" placeholder="referral, website..." {...register("source")} />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" {...register("email")} />
              {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
            </div>
            <div className="flex items-end">
              <Button type="submit" disabled={isSubmitting} className="w-full">
                {isSubmitting ? "Adding..." : "Add"}
              </Button>
            </div>
          </form>
        )}

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {data && data.length === 0 && !isError && <EmptyState title="No leads in this pipeline yet" />}

        {!isError && data && data.length > 0 && view === "kanban" && (
          <div className="grid grid-cols-1 gap-4 overflow-x-auto sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            {CRM_STAGES.map((stage) => (
              <div key={stage} className="min-w-[200px]">
                <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--bo-text-muted)]">
                  {STAGE_LABELS[stage]} ({data.filter((o) => o.stage === stage).length})
                </h3>
                <div className="space-y-2">
                  {data
                    .filter((o) => o.stage === stage)
                    .map((org) => (
                      <OrgCard key={org.id} org={org} />
                    ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {!isError && data && data.length > 0 && view === "list" && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Stage</th>
                  <th className="px-4 py-3">Owner</th>
                  <th className="px-4 py-3">Source</th>
                </tr>
              </thead>
              <tbody>
                {data.map((org) => (
                  <tr key={org.id} className="h-14 border-t border-[var(--bo-divider)]">
                    <td className="px-4 py-3">
                      <Link href={`/platform-admin/crm/${org.id}`} className="font-medium text-[var(--bo-primary)]">
                        {org.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-[var(--bo-text)]">{STAGE_LABELS[org.stage]}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{org.owner_staff_name ?? "Unassigned"}</td>
                    <td className="px-4 py-3 text-[var(--bo-text-muted)]">{org.source ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </PlatformShell>
  );
}
