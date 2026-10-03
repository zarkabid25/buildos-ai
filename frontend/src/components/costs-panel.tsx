"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCreateExpense, useProjectCostSummary, useProjectExpenses } from "@/lib/use-finance";
import { attempt, formatCurrency } from "@/lib/utils";

export function CostsPanel({ projectId }: { projectId: string }) {
  const { data: summary } = useProjectCostSummary(projectId);
  const { data: expenses } = useProjectExpenses(projectId);
  const createExpense = useCreateExpense(projectId);

  const [form, setForm] = useState({ amount: "", description: "", expense_date: "" });

  async function handleAdd() {
    if (!form.amount || !form.expense_date) return;
    if (!(await attempt(createExpense.mutateAsync(form)))) return;
    setForm({ amount: "", description: "", expense_date: "" });
  }

  return (
    <div className="space-y-4">
      {summary && (
        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink">Project Budget</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div>
              <div className="text-xs uppercase text-muted">Original Budget</div>
              <div className="text-lg font-semibold text-ink">{formatCurrency(summary.original_budget)}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-muted">Committed</div>
              <div className="text-lg font-semibold text-ink">{formatCurrency(summary.committed)}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-muted">Actual</div>
              <div className="text-lg font-semibold text-ink">{formatCurrency(summary.actual)}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-muted">Remaining</div>
              <div className="text-lg font-semibold text-ink">{formatCurrency(summary.remaining)}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-muted">Forecast</div>
              <div className="text-lg font-semibold text-ink">{formatCurrency(summary.forecast)}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-muted">Expected Variance</div>
              <div
                className={`text-lg font-semibold ${Number(summary.expected_variance) > 0 ? "text-danger" : "text-success"}`}
              >
                {Number(summary.expected_variance) > 0 ? "+" : ""}
                {formatCurrency(summary.expected_variance)}
              </div>
            </div>
          </div>
          <p className="mt-3 text-xs text-muted">{summary.forecast_basis}</p>
        </Card>
      )}

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-ink">Expenses</h2>
        <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Input
            type="number"
            placeholder="Amount"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
          />
          <Input
            type="date"
            value={form.expense_date}
            onChange={(e) => setForm({ ...form, expense_date: e.target.value })}
          />
          <Input
            placeholder="Description"
            className="sm:col-span-1"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <Button onClick={handleAdd} disabled={createExpense.isPending}>
            Add expense
          </Button>
        </div>

        {(!expenses || expenses.length === 0) && <p className="text-sm text-muted">No expenses recorded yet.</p>}
        {expenses && expenses.length > 0 && (
          <ul className="divide-y divide-border">
            {expenses.map((e) => (
              <li key={e.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <div className="text-ink">{e.description ?? "Expense"}</div>
                  <div className="text-xs text-muted">{e.expense_date}</div>
                </div>
                <span className="font-medium text-ink">{formatCurrency(e.amount)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
