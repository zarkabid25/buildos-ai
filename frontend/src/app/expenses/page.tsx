"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, QueryView } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import type { UserRole } from "@/lib/auth-types";
import { useAllExpenses, useCreateExpenseCategory, useExpenseCategories, useRecordExpense } from "@/lib/use-finance";
import { useProjects } from "@/lib/use-projects";
import { attempt, formatCurrency, localToday } from "@/lib/utils";

// Mirrors CAN_WRITE in backend/app/api/v1/finance.py; the API enforces it, this only hides the form.
const CAN_RECORD: UserRole[] = ["super_admin", "company_admin", "accountant", "project_manager"];
const selectClass = "h-9 w-full rounded-md border border-border bg-surface px-2 text-sm";

export default function ExpensesPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [projectFilter, setProjectFilter] = useState("");
  const { data: projects } = useProjects();
  const { data: categories } = useExpenseCategories();
  const expensesQuery = useAllExpenses(projectFilter || undefined);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  const projectNames = useMemo(() => new Map(projects?.map((p) => [p.id, p.name])), [projects]);
  const categoryNames = useMemo(() => new Map(categories?.map((c) => [c.id, c.name])), [categories]);

  if (authLoading || !user) return null;
  const canRecord = CAN_RECORD.includes(user.role);

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Expenses</h1>
          <p className="text-muted">Spending recorded against every project.</p>
        </div>

        {canRecord && projects && projects.length > 0 && <RecordExpense />}

        <div className="flex items-center gap-2">
          <select
            aria-label="Project"
            className="h-9 rounded-md border border-border bg-surface px-2 text-sm"
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
          >
            <option value="">All projects</option>
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <QueryView
          query={expensesQuery}
          isEmpty={(list) => list.length === 0}
          empty={<EmptyState title="No expenses recorded" hint={canRecord ? "Record one above." : undefined} />}
        >
          {(expenses) => {
            const total = expenses.reduce((sum, e) => sum + Number(e.amount), 0);
            return (
              <Card className="overflow-x-auto p-0">
                <div className="flex items-baseline justify-between px-4 pt-4">
                  <span className="text-sm text-muted">{expenses.length} expense(s)</span>
                  <span className="text-sm font-semibold text-ink">Total {formatCurrency(total)}</span>
                </div>
                <table className="w-full whitespace-nowrap text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                      <th className="px-4 py-3 font-medium">Date</th>
                      <th className="px-4 py-3 font-medium">Project</th>
                      <th className="px-4 py-3 font-medium">Category</th>
                      <th className="px-4 py-3 font-medium">Description</th>
                      <th className="px-4 py-3 text-right font-medium">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expenses.map((e) => (
                      <tr key={e.id} className="border-b border-border last:border-0">
                        <td className="px-4 py-3 text-muted">{e.expense_date}</td>
                        <td className="px-4 py-3">
                          <Link href={`/projects/${e.project_id}`} className="text-primary hover:underline">
                            {projectNames.get(e.project_id) ?? "Project"}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-muted">
                          {e.category_id ? categoryNames.get(e.category_id) ?? "—" : "Uncategorized"}
                        </td>
                        <td className="px-4 py-3 text-ink">{e.description ?? "—"}</td>
                        <td className="px-4 py-3 text-right font-medium text-ink">{formatCurrency(e.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            );
          }}
        </QueryView>
      </div>
    </AppShell>
  );
}

function RecordExpense() {
  const { data: projects } = useProjects();
  const { data: categories } = useExpenseCategories();
  const record = useRecordExpense();
  const createCategory = useCreateExpenseCategory();
  const today = localToday();
  const empty = { project_id: "", category_id: "", amount: "", expense_date: today, description: "" };
  const [form, setForm] = useState(empty);
  const [newCategory, setNewCategory] = useState("");

  async function handleSave() {
    const projectId = form.project_id || projects?.[0]?.id;
    if (!projectId || !form.amount || !form.expense_date) return;
    const saved = await attempt(
      record.mutateAsync({
        project_id: projectId,
        category_id: form.category_id || undefined,
        amount: form.amount,
        expense_date: form.expense_date,
        description: form.description.trim() || undefined,
      })
    );
    if (saved) setForm({ ...empty, project_id: projectId, category_id: form.category_id });
  }

  async function handleAddCategory() {
    if (!newCategory.trim()) return;
    const created = await attempt(createCategory.mutateAsync(newCategory.trim()));
    if (!created) return;
    setForm({ ...form, category_id: created.id });
    setNewCategory("");
  }

  return (
    <Card className="space-y-3">
      <h2 className="text-sm font-semibold text-ink">Record an expense</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div className="lg:col-span-2">
          <Label htmlFor="exp_project">Project</Label>
          <select
            id="exp_project"
            className={selectClass}
            value={form.project_id || projects?.[0]?.id || ""}
            onChange={(e) => setForm({ ...form, project_id: e.target.value })}
          >
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="exp_category">Category</Label>
          <select
            id="exp_category"
            className={selectClass}
            value={form.category_id}
            onChange={(e) => setForm({ ...form, category_id: e.target.value })}
          >
            <option value="">Uncategorized</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="exp_amount">Amount</Label>
          <Input
            id="exp_amount"
            type="number"
            min="0"
            step="0.01"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="exp_date">Date</Label>
          <Input
            id="exp_date"
            type="date"
            value={form.expense_date}
            onChange={(e) => setForm({ ...form, expense_date: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="exp_desc">Description</Label>
          <Input id="exp_desc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Input
            aria-label="New category name"
            placeholder="New category (e.g. Fuel)"
            className="w-56"
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddCategory()}
          />
          <Button variant="secondary" onClick={handleAddCategory} disabled={createCategory.isPending || !newCategory.trim()}>
            Add category
          </Button>
        </div>
        <Button onClick={handleSave} disabled={record.isPending || !form.amount || !form.expense_date}>
          {record.isPending ? "Saving..." : "Record expense"}
        </Button>
      </div>
    </Card>
  );
}
