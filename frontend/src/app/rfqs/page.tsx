"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AiNarrationPanel } from "@/components/ai-narration-panel";
import { AppShell } from "@/components/app-shell";
import { useFeedback } from "@/components/feedback";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, QueryView } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import type { UserRole } from "@/lib/auth-types";
import {
  useInviteMarketplaceSuppliers,
  useMarketplaceConnections,
  useMarketplaceStatus,
  useQuotationAttributions,
  useRfqInvitations,
} from "@/lib/use-marketplace-discovery";
import type { Rfq, RfqStatus } from "@/lib/rfq-types";
import { useMaterials } from "@/lib/use-inventory";
import { useMaterialRequests } from "@/lib/use-procurement";
import { useProjects } from "@/lib/use-projects";
import { useAwardRfq, useCancelRfq, useCreateRfq, useRecordQuotation, useRfq, useRfqs } from "@/lib/use-rfqs";
import { useSuppliers } from "@/lib/use-suppliers";
import { attempt, formatMoney } from "@/lib/utils";

// Mirror CAN_REQUEST / CAN_APPROVE in backend/app/api/v1/procurement.py; the API enforces them.
const CAN_REQUEST: UserRole[] = ["super_admin", "company_admin", "project_manager", "site_engineer", "storekeeper"];
const CAN_APPROVE: UserRole[] = ["super_admin", "company_admin", "project_manager"];
const STATUS_CLASSES: Record<RfqStatus, string> = {
  open: "bg-blue-50 text-primary",
  awarded: "bg-green-50 text-success",
  cancelled: "bg-gray-100 text-muted",
};
const selectClass = "h-9 w-full rounded-md border border-border bg-surface px-2 text-sm";

export default function RfqsPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const rfqsQuery = useRfqs();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  useEffect(() => {
    const fromLink = new URLSearchParams(window.location.search).get("rfq");
    if (fromLink) setSelectedId(fromLink);
  }, []);

  function select(id: string) {
    setSelectedId(id);
    setCreating(false);
    window.history.replaceState(null, "", `?rfq=${id}`);
  }

  if (isLoading || !user) return null;
  const canRequest = CAN_REQUEST.includes(user.role);

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-ink">RFQs &amp; Quotes</h1>
            <p className="text-muted">Ask suppliers for prices, compare their quotes side by side, and award the best one.</p>
          </div>
          {canRequest && (
            <Button onClick={() => setCreating((v) => !v)}>{creating ? "Cancel" : "+ New RFQ"}</Button>
          )}
        </div>

        {creating && <CreateRfq onCreated={(id) => select(id)} />}

        <QueryView
          query={rfqsQuery}
          isEmpty={(list) => list.length === 0}
          empty={<EmptyState title="No RFQs yet" hint={canRequest ? "Create one to start collecting quotes." : undefined} />}
        >
          {(rfqs) => (
            <Card className="overflow-x-auto p-0">
              <table className="w-full whitespace-nowrap text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                    <th className="px-4 py-3 font-medium">RFQ</th>
                    <th className="px-4 py-3 font-medium">Project</th>
                    <th className="px-4 py-3 font-medium">Due</th>
                    <th className="px-4 py-3 font-medium">Quotes</th>
                    <th className="px-4 py-3 font-medium">Lowest</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rfqs.map((r) => (
                    <tr
                      key={r.id}
                      className={`border-b border-border last:border-0 ${r.id === selectedId ? "bg-blue-50/60" : ""}`}
                    >
                      <td className="px-4 py-3">
                        <button className="text-left font-medium text-primary hover:underline" onClick={() => select(r.id)}>
                          {r.rfq_number}
                        </button>
                        <span className="ml-2 text-ink">{r.title}</span>
                      </td>
                      <td className="px-4 py-3 text-muted">{r.project_name ?? "—"}</td>
                      <td className="px-4 py-3 text-muted">{r.response_due ?? "—"}</td>
                      <td className="px-4 py-3">
                        {r.quotation_count} of {r.invited_count} invited
                      </td>
                      <td className="px-4 py-3">{r.lowest_total ? formatMoney(r.lowest_total) : "—"}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_CLASSES[r.status]}`}>
                          {r.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </QueryView>

        {selectedId && <RfqDetail key={selectedId} rfqId={selectedId} role={user.role} />}
      </div>
    </AppShell>
  );
}

function CreateRfq({ onCreated }: { onCreated: (id: string) => void }) {
  const { data: projects } = useProjects();
  const { data: materials } = useMaterials();
  const { data: suppliers } = useSuppliers();
  const { data: requests } = useMaterialRequests();
  const create = useCreateRfq();
  const [form, setForm] = useState({ title: "", project_id: "", material_request_id: "", response_due: "" });
  const [items, setItems] = useState([{ material_id: "", quantity: "" }]);
  const [invited, setInvited] = useState<string[]>([]);
  const openRequests = (requests ?? []).filter((r) => r.status === "pending" || r.status === "approved");
  const fromRequest = !!form.material_request_id;

  async function handleCreate() {
    const lines = items.filter((i) => i.material_id && Number(i.quantity) > 0);
    if (!form.title.trim() || (!fromRequest && lines.length === 0)) return;
    const rfq = await attempt(
      create.mutateAsync({
        title: form.title.trim(),
        project_id: fromRequest ? undefined : form.project_id || undefined,
        material_request_id: form.material_request_id || undefined,
        response_due: form.response_due || undefined,
        items: fromRequest ? [] : lines,
        supplier_ids: invited,
      })
    );
    if (rfq) onCreated(rfq.id);
  }

  return (
    <Card className="space-y-4">
      <h2 className="text-sm font-semibold text-ink">New request for quotation</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <Label htmlFor="rfq_title">Title</Label>
          <Input id="rfq_title" placeholder="e.g. Level 3 slab materials" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="rfq_due">Quotes due by</Label>
          <Input id="rfq_due" type="date" value={form.response_due} onChange={(e) => setForm({ ...form, response_due: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="rfq_request">From material request (optional)</Label>
          <select id="rfq_request" className={selectClass} value={form.material_request_id} onChange={(e) => setForm({ ...form, material_request_id: e.target.value })}>
            <option value="">None</option>
            {openRequests.map((r) => (
              <option key={r.id} value={r.id}>
                {r.items.length} item(s), {r.status}, {r.created_at.slice(0, 10)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {fromRequest ? (
        <p className="text-sm text-muted">The project and items will be taken from the material request.</p>
      ) : (
        <>
          <div className="max-w-sm">
            <Label htmlFor="rfq_project">Project (optional)</Label>
            <select id="rfq_project" className={selectClass} value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })}>
              <option value="">Not for a specific project</option>
              {projects?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>Items</Label>
            {items.map((item, idx) => (
              <div key={idx} className="flex flex-wrap gap-2">
                <select
                  aria-label={`Material ${idx + 1}`}
                  className="h-9 min-w-[14rem] flex-1 rounded-md border border-border bg-surface px-2 text-sm"
                  value={item.material_id}
                  onChange={(e) => setItems(items.map((it, i) => (i === idx ? { ...it, material_id: e.target.value } : it)))}
                >
                  <option value="">Choose material</option>
                  {materials?.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.unit})
                    </option>
                  ))}
                </select>
                <Input
                  aria-label={`Quantity ${idx + 1}`}
                  type="number"
                  min="0"
                  placeholder="Quantity"
                  className="w-32"
                  value={item.quantity}
                  onChange={(e) => setItems(items.map((it, i) => (i === idx ? { ...it, quantity: e.target.value } : it)))}
                />
                {items.length > 1 && (
                  <Button variant="ghost" onClick={() => setItems(items.filter((_, i) => i !== idx))}>
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button variant="secondary" onClick={() => setItems([...items, { material_id: "", quantity: "" }])}>
              + Add item
            </Button>
          </div>
        </>
      )}

      <div>
        <Label>Suppliers to ask</Label>
        <div className="mt-1 flex flex-wrap gap-3">
          {suppliers?.length === 0 && <span className="text-sm text-muted">No suppliers yet. Add them on the Suppliers page.</span>}
          {suppliers?.map((sup) => (
            <label key={sup.id} className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={invited.includes(sup.id)}
                onChange={(e) => setInvited(e.target.checked ? [...invited, sup.id] : invited.filter((x) => x !== sup.id))}
              />
              {sup.name}
            </label>
          ))}
        </div>
      </div>

      <Button onClick={handleCreate} disabled={create.isPending || !form.title.trim()}>
        {create.isPending ? "Creating..." : "Create RFQ"}
      </Button>
    </Card>
  );
}

function RfqDetail({ rfqId, role }: { rfqId: string; role: UserRole }) {
  const query = useRfq(rfqId);
  const { accessToken } = useAuth();
  return (
    <QueryView query={query}>
      {(rfq) => (
        <div className="space-y-4">
          <RfqHeader rfq={rfq} canDecide={CAN_APPROVE.includes(role)} />
          <AiNarrationPanel
            label="Ask AI to summarize this RFQ and compare quotations"
            onGenerate={() => api.get<{ narration: string }>(`/rfqs/${rfqId}/ai/summary`, accessToken ?? undefined)}
          />
          {rfq.status === "open" && CAN_REQUEST.includes(role) && <MarketplacePanel rfq={rfq} />}
          <Comparison rfq={rfq} canDecide={CAN_APPROVE.includes(role)} />
          {rfq.status === "open" && CAN_REQUEST.includes(role) && <QuoteForm rfq={rfq} />}
        </div>
      )}
    </QueryView>
  );
}

// Extends the existing RFQ page without redesigning it: same Card/Button/table
// conventions as everything else here. Shown only while the RFQ is open and
// the viewer can request quotes -- the same gate as QuoteForm below.
function MarketplacePanel({ rfq }: { rfq: Rfq }) {
  const { data: status } = useMarketplaceStatus();
  const { data: connections } = useMarketplaceConnections();
  const { data: invitations, isLoading: invitationsLoading } = useRfqInvitations(rfq.id);
  const invite = useInviteMarketplaceSuppliers(rfq.id);
  const [selected, setSelected] = useState<string[]>([]);
  const { toast } = useFeedback();

  if (status && !status.enabled) return null; // disabled for this company -- don't clutter the RFQ page

  const invitedIds = new Set((invitations ?? []).map((i) => i.marketplace_supplier_id));
  const eligible = (connections ?? []).filter((c) => c.status === "active" && c.erp_supplier_id && !invitedIds.has(c.marketplace_supplier_id));

  async function handleShare() {
    if (selected.length === 0) return;
    const saved = await attempt(invite.mutateAsync(selected));
    if (saved) {
      setSelected([]);
      toast(`Shared with ${saved.length} marketplace supplier(s).`, "success");
    }
  }

  return (
    <Card className="space-y-3">
      <h3 className="text-sm font-semibold text-ink">Marketplace suppliers</h3>

      {eligible.length === 0 && (connections ?? []).length === 0 && (
        <p className="text-sm text-muted">
          No connected marketplace suppliers yet. Find and connect to one on the{" "}
          <Link href="/marketplace" className="underline">
            Supplier Marketplace
          </Link>{" "}
          page first.
        </p>
      )}
      {eligible.length > 0 && (
        <>
          <p className="text-sm text-muted">Share this RFQ with connected marketplace suppliers to collect their quotes too.</p>
          <div className="flex flex-wrap gap-3">
            {eligible.map((c) => (
              <label key={c.id} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={selected.includes(c.marketplace_supplier_id)}
                  onChange={(e) =>
                    setSelected(e.target.checked ? [...selected, c.marketplace_supplier_id] : selected.filter((x) => x !== c.marketplace_supplier_id))
                  }
                />
                {c.marketplace_supplier_name}
                {c.is_preferred && <span className="text-xs text-primary">(preferred)</span>}
              </label>
            ))}
          </div>
          <Button variant="secondary" onClick={handleShare} disabled={selected.length === 0 || invite.isPending}>
            {invite.isPending ? "Sharing..." : "Share RFQ with selected suppliers"}
          </Button>
        </>
      )}

      {!invitationsLoading && invitations && invitations.length > 0 && (
        <div className="overflow-x-auto pt-2">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="py-2 pr-4 font-medium">Marketplace supplier</th>
                <th className="py-2 pr-4 font-medium">Invitation status</th>
              </tr>
            </thead>
            <tbody>
              {invitations.map((inv) => (
                <tr key={inv.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-4 text-ink">{inv.marketplace_supplier_name}</td>
                  <td className="py-2 pr-4 capitalize text-muted">{inv.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function RfqHeader({ rfq, canDecide }: { rfq: Rfq; canDecide: boolean }) {
  const cancel = useCancelRfq(rfq.id);
  const { confirm } = useFeedback();
  return (
    <Card className="space-y-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold text-ink">
          {rfq.rfq_number}: {rfq.title}
        </h2>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_CLASSES[rfq.status]}`}>{rfq.status}</span>
      </div>
      <p className="text-sm text-muted">
        {rfq.project_name ? `Project: ${rfq.project_name}` : "Not for a specific project"}
        {rfq.response_due && ` · quotes due ${rfq.response_due}`}
        {` · asked: ${rfq.invited.map((s) => `${s.supplier_name}${s.has_quoted ? " ✓" : ""}`).join(", ") || "nobody yet"}`}
      </p>
      {rfq.status === "awarded" && rfq.purchase_order_id && (
        <p className="text-sm text-success">
          Awarded. {rfq.po_number} was drafted at the quoted rates and is waiting for approval on the{" "}
          <Link href="/procurement" className="underline">
            Purchase Orders
          </Link>{" "}
          page.
        </p>
      )}
      {rfq.status === "open" && canDecide && (
        <Button
          variant="ghost"
          className="px-0 text-muted hover:text-danger"
          onClick={async () => {
            const ok = await confirm({ title: `Cancel ${rfq.rfq_number}?`, body: "No more quotes can be added and nothing can be awarded.", confirmLabel: "Cancel RFQ", danger: true });
            if (ok) cancel.mutate();
          }}
        >
          Cancel this RFQ
        </Button>
      )}
    </Card>
  );
}

function Comparison({ rfq, canDecide }: { rfq: Rfq; canDecide: boolean }) {
  const award = useAwardRfq(rfq.id);
  const { confirm } = useFeedback();
  // The honest record of who actually entered a quote on a marketplace
  // supplier's behalf -- separate from (and never overriding) the RFQ's own
  // created_by data, which keeps meaning what it always meant.
  const { data: attributions } = useQuotationAttributions(rfq.id);
  const attributionByQuotation = new Map((attributions ?? []).map((a) => [a.quotation_id, a]));

  if (rfq.quotations.length === 0) {
    return <EmptyState title="No quotes yet" hint="Enter each supplier's prices below as they come in." />;
  }

  async function handleAward(q: Rfq["quotations"][number]) {
    const ok = await confirm({
      title: `Award to ${q.supplier_name}?`,
      body: `This drafts a purchase order for ${formatMoney(q.total)} at ${q.supplier_name}'s rates. The PO still needs approval before anything is ordered.`,
      confirmLabel: "Award and draft PO",
    });
    if (ok) award.mutate(q.id);
  }

  return (
    <Card className="overflow-x-auto p-0">
      <div className="px-4 pt-4">
        <h3 className="text-sm font-semibold text-ink">Quote comparison</h3>
        <p className="text-xs text-muted">Cheapest rate per item and cheapest total are highlighted. Rates are per unit.</p>
      </div>
      <table className="w-full whitespace-nowrap text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
            <th className="px-4 py-3 font-medium">Item</th>
            {rfq.quotations.map((q) => {
              const attribution = attributionByQuotation.get(q.id);
              return (
                <th key={q.id} className="px-4 py-3 font-medium">
                  {q.supplier_name}
                  {q.id === rfq.awarded_quotation_id && <span className="ml-1 normal-case text-success">(awarded)</span>}
                  {attribution && (
                    <div className="mt-0.5 text-xs font-normal normal-case text-muted">
                      Entered by {attribution.submitted_by_staff_name} (BuildOS staff) on behalf of {attribution.marketplace_supplier_name}
                    </div>
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rfq.items.map((item) => (
            <tr key={item.id} className="border-b border-border">
              <td className="px-4 py-3">
                <span className="text-ink">{item.material_name}</span>
                <span className="ml-1 text-xs text-muted">
                  {item.quantity} {item.unit}
                </span>
              </td>
              {rfq.quotations.map((q) => {
                const line = q.items.find((qi) => qi.rfq_item_id === item.id);
                return (
                  <td key={q.id} className={`px-4 py-3 ${line?.is_lowest ? "font-medium text-success" : "text-ink"}`}>
                    {line ? formatMoney(line.rate) : "—"}
                    {line && <span className="ml-1 text-xs text-muted">= {formatMoney(line.amount)}</span>}
                  </td>
                );
              })}
            </tr>
          ))}
          <tr className="border-b border-border bg-gray-50/60">
            <td className="px-4 py-3 font-semibold text-ink">Total</td>
            {rfq.quotations.map((q) => (
              <td key={q.id} className={`px-4 py-3 font-semibold ${q.is_lowest_total ? "text-success" : "text-ink"}`}>
                {formatMoney(q.total)}
                {q.is_lowest_total && <span className="ml-1 text-xs font-normal">lowest</span>}
              </td>
            ))}
          </tr>
          <tr className="border-b border-border">
            <td className="px-4 py-3 text-muted">Delivery</td>
            {rfq.quotations.map((q) => (
              <td key={q.id} className="px-4 py-3 text-muted">
                {q.delivery_days !== null ? `${q.delivery_days} days` : "—"}
              </td>
            ))}
          </tr>
          <tr className="border-b border-border">
            <td className="px-4 py-3 text-muted">Valid until</td>
            {rfq.quotations.map((q) => (
              <td key={q.id} className={`px-4 py-3 ${q.expired ? "font-medium text-danger" : "text-muted"}`}>
                {q.valid_until ?? "—"}
                {q.expired && " (expired)"}
              </td>
            ))}
          </tr>
          {rfq.status === "open" && canDecide && (
            <tr>
              <td className="px-4 py-3" />
              {rfq.quotations.map((q) => (
                <td key={q.id} className="px-4 py-3">
                  <Button variant={q.is_lowest_total ? "primary" : "secondary"} disabled={q.expired || award.isPending} onClick={() => handleAward(q)}>
                    Award
                  </Button>
                </td>
              ))}
            </tr>
          )}
        </tbody>
      </table>
    </Card>
  );
}

function QuoteForm({ rfq }: { rfq: Rfq }) {
  const { data: suppliers } = useSuppliers();
  const record = useRecordQuotation(rfq.id);
  const [supplierId, setSupplierId] = useState("");
  const [rates, setRates] = useState<Record<string, string>>({});
  const [extra, setExtra] = useState({ delivery_days: "", valid_until: "", notes: "" });
  const existing = rfq.quotations.find((q) => q.supplier_id === supplierId);
  const complete = !!supplierId && rfq.items.every((i) => rates[i.id] !== undefined && rates[i.id] !== "" && Number(rates[i.id]) >= 0);

  function pickSupplier(id: string) {
    setSupplierId(id);
    // Re-entering a quote starts from what's already recorded for that supplier.
    const q = rfq.quotations.find((x) => x.supplier_id === id);
    setRates(q ? Object.fromEntries(q.items.map((qi) => [qi.rfq_item_id, String(Number(qi.rate))])) : {});
    setExtra({
      delivery_days: q?.delivery_days != null ? String(q.delivery_days) : "",
      valid_until: q?.valid_until ?? "",
      notes: q?.notes ?? "",
    });
  }

  async function handleSave() {
    if (!complete) return;
    const saved = await attempt(
      record.mutateAsync({
        supplier_id: supplierId,
        delivery_days: extra.delivery_days ? Number(extra.delivery_days) : undefined,
        valid_until: extra.valid_until || undefined,
        notes: extra.notes.trim() || undefined,
        items: rfq.items.map((i) => ({ rfq_item_id: i.id, rate: rates[i.id] })),
      })
    );
    if (saved) {
      setSupplierId("");
      setRates({});
      setExtra({ delivery_days: "", valid_until: "", notes: "" });
    }
  }

  return (
    <Card className="space-y-3">
      <h3 className="text-sm font-semibold text-ink">Enter a supplier&apos;s quote</h3>
      <div className="max-w-sm">
        <Label htmlFor="q_supplier">Supplier</Label>
        <select id="q_supplier" className={selectClass} value={supplierId} onChange={(e) => pickSupplier(e.target.value)}>
          <option value="">Choose supplier</option>
          {suppliers?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
              {rfq.quotations.some((q) => q.supplier_id === s.id) ? " (has quoted; re-enter to update)" : ""}
            </option>
          ))}
        </select>
      </div>
      {supplierId && (
        <>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {rfq.items.map((i) => (
              <div key={i.id}>
                <Label htmlFor={`rate_${i.id}`}>
                  {i.material_name}: rate per {i.unit} ({i.quantity} needed)
                </Label>
                <Input
                  id={`rate_${i.id}`}
                  type="number"
                  min="0"
                  step="0.01"
                  value={rates[i.id] ?? ""}
                  onChange={(e) => setRates({ ...rates, [i.id]: e.target.value })}
                />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <div>
              <Label htmlFor="q_days">Delivery (days)</Label>
              <Input id="q_days" type="number" min="0" value={extra.delivery_days} onChange={(e) => setExtra({ ...extra, delivery_days: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="q_valid">Quote valid until</Label>
              <Input id="q_valid" type="date" value={extra.valid_until} onChange={(e) => setExtra({ ...extra, valid_until: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="q_notes">Notes</Label>
              <Input id="q_notes" value={extra.notes} onChange={(e) => setExtra({ ...extra, notes: e.target.value })} />
            </div>
          </div>
          <Button onClick={handleSave} disabled={!complete || record.isPending}>
            {record.isPending ? "Saving..." : existing ? "Update quote" : "Save quote"}
          </Button>
          {!complete && <p className="text-xs text-muted">Enter a rate for every item to save the quote.</p>}
        </>
      )}
    </Card>
  );
}
