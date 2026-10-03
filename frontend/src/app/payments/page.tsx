"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { QueryView } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import type { UserRole } from "@/lib/auth-types";
import type { PaymentMethod } from "@/lib/rfq-types";
import { usePurchaseOrders } from "@/lib/use-procurement";
import { useProjects } from "@/lib/use-projects";
import {
  useCashSummary,
  useClientReceipts,
  useRecordClientReceipt,
  useRecordSupplierPayment,
  useSupplierPayments,
} from "@/lib/use-rfqs";
import { useSuppliers } from "@/lib/use-suppliers";
import { attempt, formatMoney, localToday } from "@/lib/utils";

// Mirrors CAN_RECORD in backend/app/api/v1/payments.py; the API enforces it.
const CAN_RECORD: UserRole[] = ["super_admin", "company_admin", "accountant"];
const METHODS: { value: PaymentMethod; label: string }[] = [
  { value: "bank_transfer", label: "Bank transfer" },
  { value: "cheque", label: "Cheque" },
  { value: "cash", label: "Cash" },
  { value: "other", label: "Other" },
];
const methodLabel = (m: PaymentMethod) => METHODS.find((x) => x.value === m)?.label ?? m;
const selectClass = "h-9 w-full rounded-md border border-border bg-surface px-2 text-sm";

export default function PaymentsPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const summaryQuery = useCashSummary();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) return null;
  const canRecord = CAN_RECORD.includes(user.role);

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Payments</h1>
          <p className="text-muted">Money paid to suppliers, money received from clients, and what&apos;s still owed.</p>
        </div>

        <QueryView query={summaryQuery}>
          {(summary) => (
            <>
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                {[
                  { label: "Received from clients", value: summary.total_received, tone: "text-ink" },
                  { label: "Paid to suppliers", value: summary.total_paid_out, tone: "text-ink" },
                  { label: "Net cash", value: summary.net, tone: Number(summary.net) < 0 ? "text-danger" : "text-success" },
                  { label: "Owed to suppliers", value: summary.total_outstanding, tone: Number(summary.total_outstanding) > 0 ? "text-warning" : "text-ink" },
                ].map((s) => (
                  <Card key={s.label}>
                    <div className="text-xs uppercase tracking-wide text-muted">{s.label}</div>
                    <div className={`text-xl font-semibold ${s.tone}`}>{formatMoney(s.value)}</div>
                  </Card>
                ))}
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <Card className="overflow-x-auto p-0">
                  <h2 className="px-4 pt-4 text-sm font-semibold text-ink">Cash by project</h2>
                  {summary.projects.length === 0 ? (
                    <p className="px-4 py-4 text-sm text-muted">No money in or out yet.</p>
                  ) : (
                    <table className="w-full whitespace-nowrap text-sm">
                      <thead>
                        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                          <th className="px-4 py-3 font-medium">Project</th>
                          <th className="px-4 py-3 font-medium">Received</th>
                          <th className="px-4 py-3 font-medium">Paid out</th>
                          <th className="px-4 py-3 font-medium">Net</th>
                        </tr>
                      </thead>
                      <tbody>
                        {summary.projects.map((p) => (
                          <tr key={p.project_id ?? "none"} className="border-b border-border last:border-0">
                            <td className="px-4 py-3 text-ink">{p.project_name}</td>
                            <td className="px-4 py-3">{formatMoney(p.received)}</td>
                            <td className="px-4 py-3">{formatMoney(p.paid_out)}</td>
                            <td className={`px-4 py-3 font-medium ${Number(p.net) < 0 ? "text-danger" : "text-success"}`}>
                              {formatMoney(p.net)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </Card>

                <Card className="overflow-x-auto p-0">
                  <h2 className="px-4 pt-4 text-sm font-semibold text-ink">Owed to suppliers</h2>
                  {summary.payables.length === 0 ? (
                    <p className="px-4 py-4 text-sm text-muted">No approved purchase orders yet.</p>
                  ) : (
                    <table className="w-full whitespace-nowrap text-sm">
                      <thead>
                        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                          <th className="px-4 py-3 font-medium">Supplier</th>
                          <th className="px-4 py-3 font-medium">Ordered</th>
                          <th className="px-4 py-3 font-medium">Paid</th>
                          <th className="px-4 py-3 font-medium">Outstanding</th>
                        </tr>
                      </thead>
                      <tbody>
                        {summary.payables.map((p) => (
                          <tr key={p.supplier_id} className="border-b border-border last:border-0">
                            <td className="px-4 py-3 text-ink">{p.supplier_name}</td>
                            <td className="px-4 py-3">{formatMoney(p.committed)}</td>
                            <td className="px-4 py-3">{formatMoney(p.paid)}</td>
                            <td className={`px-4 py-3 font-medium ${Number(p.outstanding) > 0 ? "text-warning" : "text-success"}`}>
                              {formatMoney(p.outstanding)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  <p className="px-4 pb-3 text-xs text-muted">Counts approved purchase orders only; drafts and pending ones aren&apos;t owed yet.</p>
                </Card>
              </div>
            </>
          )}
        </QueryView>

        {canRecord && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <PaySupplier />
            <ReceiveFromClient />
          </div>
        )}

        <History />
      </div>
    </AppShell>
  );
}

function PaySupplier() {
  const { data: orders } = usePurchaseOrders();
  const { data: suppliers } = useSuppliers();
  const record = useRecordSupplierPayment();
  const supplierNames = useMemo(() => new Map(suppliers?.map((s) => [s.id, s.name])), [suppliers]);
  const payable = (orders ?? []).filter(
    (o) => ["approved", "partially_received", "received"].includes(o.status) && o.payment_status !== "paid"
  );
  const empty = { purchase_order_id: "", amount: "", paid_on: localToday(), method: "bank_transfer" as PaymentMethod, reference: "" };
  const [form, setForm] = useState(empty);
  const selected = payable.find((o) => o.id === form.purchase_order_id);
  const outstanding = selected ? Number(selected.total_amount) - Number(selected.amount_paid) : 0;

  async function handleSave() {
    if (!form.purchase_order_id || !form.amount) return;
    const saved = await attempt(
      record.mutateAsync({ ...form, reference: form.reference.trim() || undefined })
    );
    if (saved) setForm(empty);
  }

  return (
    <Card className="space-y-3">
      <h2 className="text-sm font-semibold text-ink">Pay a supplier</h2>
      {payable.length === 0 ? (
        <p className="text-sm text-muted">No approved purchase orders with money outstanding.</p>
      ) : (
        <>
          <div>
            <Label htmlFor="pay_po">Purchase order</Label>
            <select
              id="pay_po"
              className={selectClass}
              value={form.purchase_order_id}
              onChange={(e) => {
                const po = payable.find((o) => o.id === e.target.value);
                const owed = po ? (Number(po.total_amount) - Number(po.amount_paid)).toFixed(2) : "";
                setForm({ ...form, purchase_order_id: e.target.value, amount: owed });
              }}
            >
              <option value="">Choose purchase order</option>
              {payable.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.po_number} · {supplierNames.get(o.supplier_id) ?? "Supplier"} · owed{" "}
                  {formatMoney(Number(o.total_amount) - Number(o.amount_paid))}
                </option>
              ))}
            </select>
          </div>
          <PaymentFields form={form} setForm={setForm} dateField="paid_on" />
          {selected && Number(form.amount) > outstanding && (
            <p className="text-xs text-danger">That&apos;s more than the {formatMoney(outstanding)} outstanding on {selected.po_number}.</p>
          )}
          <Button onClick={handleSave} disabled={record.isPending || !form.purchase_order_id || !form.amount}>
            {record.isPending ? "Saving..." : "Record payment"}
          </Button>
        </>
      )}
    </Card>
  );
}

function ReceiveFromClient() {
  const { data: projects } = useProjects();
  const record = useRecordClientReceipt();
  const empty = { project_id: "", amount: "", received_on: localToday(), method: "bank_transfer" as PaymentMethod, reference: "" };
  const [form, setForm] = useState(empty);

  async function handleSave() {
    const projectId = form.project_id || projects?.[0]?.id;
    if (!projectId || !form.amount) return;
    const saved = await attempt(
      record.mutateAsync({ ...form, project_id: projectId, reference: form.reference.trim() || undefined })
    );
    if (saved) setForm({ ...empty, project_id: projectId });
  }

  return (
    <Card className="space-y-3">
      <h2 className="text-sm font-semibold text-ink">Receive from a client</h2>
      <div>
        <Label htmlFor="rec_project">Project</Label>
        <select
          id="rec_project"
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
      <PaymentFields form={form} setForm={setForm} dateField="received_on" />
      <Button onClick={handleSave} disabled={record.isPending || !form.amount || !projects?.length}>
        {record.isPending ? "Saving..." : "Record receipt"}
      </Button>
    </Card>
  );
}

type PaymentForm = { amount: string; method: PaymentMethod; reference: string; paid_on?: string; received_on?: string };

function PaymentFields<T extends PaymentForm>({
  form,
  setForm,
  dateField,
}: {
  form: T;
  setForm: (f: T) => void;
  dateField: "paid_on" | "received_on";
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <div>
        <Label htmlFor={`${dateField}_amount`}>Amount</Label>
        <Input id={`${dateField}_amount`} type="number" min="0" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
      </div>
      <div>
        <Label htmlFor={`${dateField}_date`}>Date</Label>
        <Input id={`${dateField}_date`} type="date" value={form[dateField] ?? ""} onChange={(e) => setForm({ ...form, [dateField]: e.target.value })} />
      </div>
      <div>
        <Label htmlFor={`${dateField}_method`}>Method</Label>
        <select id={`${dateField}_method`} className={selectClass} value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value as PaymentMethod })}>
          {METHODS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <Label htmlFor={`${dateField}_ref`}>Reference</Label>
        <Input id={`${dateField}_ref`} placeholder="Cheque / transfer no." value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
      </div>
    </div>
  );
}

function History() {
  const { data: payments } = useSupplierPayments();
  const { data: receipts } = useClientReceipts();
  const rows = [
    ...(payments ?? []).map((p) => ({
      id: p.id, date: p.paid_on, kind: "Paid" as const, who: `${p.supplier_name ?? "Supplier"} · ${p.po_number ?? ""}`,
      method: p.method, reference: p.reference, amount: p.amount,
    })),
    ...(receipts ?? []).map((r) => ({
      id: r.id, date: r.received_on, kind: "Received" as const, who: r.project_name ?? "Project",
      method: r.method, reference: r.reference, amount: r.amount,
    })),
  ].sort((a, b) => b.date.localeCompare(a.date));

  return (
    <Card className="overflow-x-auto p-0">
      <h2 className="px-4 pt-4 text-sm font-semibold text-ink">History</h2>
      {rows.length === 0 ? (
        <p className="px-4 py-4 text-sm text-muted">Nothing recorded yet.</p>
      ) : (
        <table className="w-full whitespace-nowrap text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">To / from</th>
              <th className="px-4 py-3 font-medium">Method</th>
              <th className="px-4 py-3 font-medium">Reference</th>
              <th className="px-4 py-3 text-right font-medium">Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 text-muted">{r.date}</td>
                <td className={`px-4 py-3 ${r.kind === "Received" ? "text-success" : "text-ink"}`}>{r.kind}</td>
                <td className="px-4 py-3 text-ink">{r.who}</td>
                <td className="px-4 py-3 text-muted">{methodLabel(r.method)}</td>
                <td className="px-4 py-3 text-muted">{r.reference ?? "—"}</td>
                <td className={`px-4 py-3 text-right font-medium ${r.kind === "Received" ? "text-success" : "text-ink"}`}>
                  {r.kind === "Received" ? "+" : "−"}
                  {formatMoney(r.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="px-4 pb-3 text-xs text-muted">Payments can&apos;t be edited or deleted; every one is also in the activity log.</p>
    </Card>
  );
}
