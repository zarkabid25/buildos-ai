"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { useCreatePlatformPlan, usePlatformPlans, useUpdatePlatformPlan } from "@/lib/use-platform-billing";

interface PlanFormInput {
  name: string;
  description: string;
  trial_days: string;
  max_projects: string;
  max_team_members: string;
  storage_gb: string;
  marketplace_included: boolean;
  monthly_price: string;
  annual_price: string;
}

export default function PlatformPlansPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast } = useFeedback();
  const isReadOnly = admin?.role === "support";
  const [showForm, setShowForm] = useState(false);

  const { data: plans, isLoading: plansLoading, isError, error, refetch } = usePlatformPlans(true);
  const createPlan = useCreatePlatformPlan();
  const updatePlan = useUpdatePlatformPlan();

  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<PlanFormInput>({
    defaultValues: { trial_days: "0", max_projects: "", max_team_members: "", storage_gb: "", marketplace_included: false, monthly_price: "", annual_price: "" },
  });

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function onSubmit(values: PlanFormInput) {
    try {
      const prices = [];
      if (values.monthly_price) prices.push({ currency: "USD", billing_period: "monthly" as const, amount: values.monthly_price });
      if (values.annual_price) prices.push({ currency: "USD", billing_period: "annual" as const, amount: values.annual_price });
      await createPlan.mutateAsync({
        name: values.name,
        description: values.description || undefined,
        trial_days: Number(values.trial_days) || 0,
        max_projects: values.max_projects ? Number(values.max_projects) : null,
        max_team_members: values.max_team_members ? Number(values.max_team_members) : null,
        storage_gb: values.storage_gb ? Number(values.storage_gb) : null,
        marketplace_included: values.marketplace_included,
        prices,
      });
      reset();
      setShowForm(false);
      toast("Plan created.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function toggleActive(planId: string, isActive: boolean) {
    try {
      await updatePlan.mutateAsync({ planId, is_active: !isActive });
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Plans">
      <div className="space-y-5">
        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Subscription Plans</h1>
              <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">Configured here, never hardcoded in the frontend.</p>
            </div>
            {!isReadOnly && <Button onClick={() => setShowForm((s) => !s)}>Add plan</Button>}
          </div>

          {showForm && (
            <form onSubmit={handleSubmit(onSubmit)} className="mt-4 grid gap-3 border-t border-[var(--bo-divider)] pt-4 sm:grid-cols-4">
              <div>
                <Label htmlFor="name">Name</Label>
                <Input id="name" {...register("name", { required: true })} />
              </div>
              <div>
                <Label htmlFor="trial_days">Trial days</Label>
                <Input id="trial_days" type="number" {...register("trial_days")} />
              </div>
              <div>
                <Label htmlFor="max_projects">Max projects</Label>
                <Input id="max_projects" type="number" placeholder="blank = unlimited" {...register("max_projects")} />
              </div>
              <div>
                <Label htmlFor="max_team_members">Max team members</Label>
                <Input id="max_team_members" type="number" placeholder="blank = unlimited" {...register("max_team_members")} />
              </div>
              <div>
                <Label htmlFor="monthly_price">Monthly price (USD)</Label>
                <Input id="monthly_price" {...register("monthly_price")} />
              </div>
              <div>
                <Label htmlFor="annual_price">Annual price (USD)</Label>
                <Input id="annual_price" {...register("annual_price")} />
              </div>
              <div className="flex items-end gap-2">
                <label className="flex items-center gap-1.5 text-sm text-[var(--bo-text)]">
                  <input type="checkbox" {...register("marketplace_included")} /> Marketplace included
                </label>
              </div>
              <div className="flex items-end">
                <Button type="submit" disabled={isSubmitting} className="w-full">
                  {isSubmitting ? "Creating..." : "Create plan"}
                </Button>
              </div>
            </form>
          )}
        </div>

        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {!plansLoading && plans && (
          <div className="overflow-x-auto rounded-lg border border-[var(--bo-divider)] bg-[var(--bo-surface)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                <tr>
                  <th className="px-4 py-3">Plan</th>
                  <th className="px-4 py-3">Monthly</th>
                  <th className="px-4 py-3">Annual</th>
                  <th className="px-4 py-3">Projects</th>
                  <th className="px-4 py-3">Team</th>
                  <th className="px-4 py-3">Marketplace</th>
                  <th className="px-4 py-3">Status</th>
                  {!isReadOnly && <th className="px-4 py-3"></th>}
                </tr>
              </thead>
              <tbody>
                {plans.map((plan) => {
                  const monthly = plan.prices.find((p) => p.billing_period === "monthly" && p.is_current);
                  const annual = plan.prices.find((p) => p.billing_period === "annual" && p.is_current);
                  return (
                    <tr key={plan.id} className="h-14 border-t border-[var(--bo-divider)]">
                      <td className="px-4 py-3 font-medium text-[var(--bo-text)]">{plan.name}</td>
                      <td className="bo-tabular px-4 py-3 text-[var(--bo-text)]">{monthly ? `${monthly.amount} ${monthly.currency}` : "—"}</td>
                      <td className="bo-tabular px-4 py-3 text-[var(--bo-text)]">{annual ? `${annual.amount} ${annual.currency}` : "—"}</td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{plan.max_projects ?? "Unlimited"}</td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{plan.max_team_members ?? "Unlimited"}</td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{plan.marketplace_included ? "Yes" : "No"}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${plan.is_active ? "bg-[var(--bo-success-bg)] text-[var(--bo-success)]" : "bg-[var(--bo-danger-bg)] text-[var(--bo-danger)]"}`}>
                          {plan.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      {!isReadOnly && (
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => toggleActive(plan.id, plan.is_active)} className="h-9 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm font-medium text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]">
                            {plan.is_active ? "Deactivate" : "Activate"}
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </PlatformShell>
  );
}
