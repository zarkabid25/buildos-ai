"use client";

import { useState } from "react";

import { BoqVsActualPanel } from "@/components/boq-vs-actual-panel";
import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import type { BoqAiGeneratedItem } from "@/lib/boq-types";
import {
  useAcceptAiBoq,
  useBoqItems,
  useBoqSummary,
  useCreateBoqItem,
  useDeleteBoqItem,
  useGenerateAiBoq,
} from "@/lib/use-boq";
import { useMaterials } from "@/lib/use-inventory";
import { attempt, formatCurrency } from "@/lib/utils";

export function BoqPanel({ projectId }: { projectId: string }) {
  const { data: items } = useBoqItems(projectId);
  const { data: summary } = useBoqSummary(projectId);
  const createItem = useCreateBoqItem(projectId);
  const deleteItem = useDeleteBoqItem(projectId);
  const generateAi = useGenerateAiBoq(projectId);
  const acceptAi = useAcceptAiBoq(projectId);
  const { data: materials } = useMaterials();
  const { confirm } = useFeedback();

  const emptyForm = { item_code: "", description: "", unit: "", quantity: "", rate: "", material_id: "" };
  const [form, setForm] = useState(emptyForm);
  const [draft, setDraft] = useState<BoqAiGeneratedItem[] | null>(null);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);

  async function handleAdd() {
    if (!form.item_code || !form.description || !form.unit) return;
    try {
      await createItem.mutateAsync({
        item_code: form.item_code,
        description: form.description,
        unit: form.unit,
        quantity: form.quantity || "0",
        rate: form.rate || "0",
        material_id: form.material_id || null,
      });
    } catch {
      return; // shown below via createItem.error
    }
    setForm(emptyForm);
  }

  async function handleGenerate() {
    const res = await attempt(generateAi.mutateAsync({ project_type: "residential" }));
    if (!res) return;
    setDraft(res.items);
    setDisclaimer(res.disclaimer);
  }

  async function handleAcceptDraft() {
    if (!draft) return;
    if (!(await attempt(acceptAi.mutateAsync(draft)))) return;
    setDraft(null);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted">
          {summary ? `${summary.item_count} items · ${formatCurrency(summary.total_amount)} total` : ""}
        </div>
        <Button variant="secondary" onClick={handleGenerate} disabled={generateAi.isPending}>
          ✨ {generateAi.isPending ? "Generating..." : "Generate BOQ with AI"}
        </Button>
      </div>

      {draft && (
        <Card className="border-primary/40 bg-blue-50/40">
          <h3 className="mb-1 text-sm font-semibold text-ink">AI-generated draft — review before adding</h3>
          <p className="mb-3 text-xs text-muted">{disclaimer}</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-muted">
                <th className="py-1">Item</th>
                <th className="py-1">Description</th>
                <th className="py-1">Unit</th>
                <th className="py-1">Qty</th>
                <th className="py-1">Rate</th>
              </tr>
            </thead>
            <tbody>
              {draft.map((d) => (
                <tr key={d.item_code} className="border-t border-border/60">
                  <td className="py-1">{d.item_code}</td>
                  <td className="py-1">{d.description}</td>
                  <td className="py-1">{d.unit}</td>
                  <td className="py-1">{d.quantity}</td>
                  <td className="py-1">{d.rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 flex gap-2">
            <Button onClick={handleAcceptDraft} disabled={acceptAi.isPending}>
              {acceptAi.isPending ? "Adding..." : `Add all ${draft.length} items`}
            </Button>
            <Button variant="secondary" onClick={() => setDraft(null)}>
              Discard
            </Button>
          </div>
        </Card>
      )}

      <Card>
        <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
          <div>
            <Label htmlFor="boq_code">Item</Label>
            <Input id="boq_code" value={form.item_code} onChange={(e) => setForm({ ...form, item_code: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="boq_desc">Description</Label>
            <Input id="boq_desc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="boq_material">Inventory material (for BOQ vs actual)</Label>
            <select
              id="boq_material"
              className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
              value={form.material_id}
              onChange={(e) => {
                const material = materials?.find((m) => m.id === e.target.value);
                setForm({ ...form, material_id: e.target.value, unit: material ? material.unit : form.unit });
              }}
            >
              <option value="">Not linked</option>
              {materials?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.unit})
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="boq_unit">Unit</Label>
            <Input id="boq_unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="boq_qty">Qty</Label>
            <Input id="boq_qty" type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="boq_rate">Rate</Label>
            <Input id="boq_rate" type="number" value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} />
          </div>
          <div className="flex items-end">
            <Button onClick={handleAdd} disabled={createItem.isPending} className="w-full">
              Add item
            </Button>
          </div>
        </div>

        {createItem.error && (
          <p className="mb-2 text-sm text-danger">
            {createItem.error instanceof ApiError ? createItem.error.message : "Could not add that item"}
          </p>
        )}

        {(!items || items.length === 0) && <p className="text-sm text-muted">No BOQ items yet.</p>}

        {items && items.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-2 py-2">Item</th>
                <th className="px-2 py-2">Description</th>
                <th className="px-2 py-2">Unit</th>
                <th className="px-2 py-2">Qty</th>
                <th className="px-2 py-2">Rate</th>
                <th className="px-2 py-2">Amount</th>
                <th className="px-2 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-border last:border-0">
                  <td className="px-2 py-2">
                    {item.item_code}
                    {item.is_ai_generated && (
                      <span className="ml-1 rounded bg-blue-100 px-1 text-[10px] text-blue-700">AI</span>
                    )}
                  </td>
                  <td className="px-2 py-2">{item.description}</td>
                  <td className="px-2 py-2 text-muted">{item.unit}</td>
                  <td className="px-2 py-2">{item.quantity}</td>
                  <td className="px-2 py-2">{formatCurrency(item.rate)}</td>
                  <td className="px-2 py-2 font-medium">{formatCurrency(item.amount)}</td>
                  <td className="px-2 py-2 text-right">
                    <button
                      onClick={async () => {
                        const ok = await confirm({
                          title: `Remove BOQ item ${item.item_code}?`,
                          body: `${item.description} (${formatCurrency(item.amount)}) will be removed from the BOQ.`,
                          confirmLabel: "Remove",
                          danger: true,
                        });
                        if (ok) deleteItem.mutate(item.id);
                      }}
                      className="text-xs text-muted hover:text-danger"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <BoqVsActualPanel projectId={projectId} />
    </div>
  );
}
