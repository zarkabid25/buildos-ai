"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState, TableSkeleton } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import type {
  ExpenseReport,
  InventoryReport,
  Period,
  ProcurementReport,
  ProjectReport,
  ReportKind,
} from "@/lib/report-types";
import { downloadReportCsv, useReport } from "@/lib/use-reports";
import { formatCurrency } from "@/lib/utils";

const REPORTS: { kind: ReportKind; label: string; hasPeriod: boolean }[] = [
  { kind: "projects", label: "Projects", hasPeriod: false },
  { kind: "inventory", label: "Inventory", hasPeriod: true },
  { kind: "procurement", label: "Procurement", hasPeriod: true },
  { kind: "expenses", label: "Expenses", hasPeriod: true },
];

const label = (s: string) => s.replace(/_/g, " ");

export default function ReportsPage() {
  const { user, isLoading, accessToken } = useAuth();
  const router = useRouter();
  const [kind, setKind] = useState<ReportKind>("projects");
  const [period, setPeriod] = useState<Period>({});
  const [downloadError, setDownloadError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) return null;
  const current = REPORTS.find((r) => r.kind === kind)!;
  const effectivePeriod = current.hasPeriod ? period : {};
  const badPeriod = !!(period.date_from && period.date_to && period.date_from > period.date_to);

  async function handleDownload() {
    if (!accessToken) return;
    setDownloadError(null);
    try {
      await downloadReportCsv(kind, effectivePeriod, accessToken);
    } catch {
      setDownloadError("Could not download the report.");
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-ink">Reports</h1>
            <p className="text-muted">Calculated from your records, the same numbers the rest of the app shows.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => window.print()}>
              Print
            </Button>
            <Button onClick={handleDownload} disabled={badPeriod}>
              Download CSV
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <div className="flex gap-1 overflow-x-auto border-b border-border">
            {REPORTS.map((r) => (
              <button
                key={r.kind}
                onClick={() => setKind(r.kind)}
                className={`shrink-0 whitespace-nowrap px-3 py-2 text-sm ${
                  kind === r.kind ? "border-b-2 border-primary font-medium text-ink" : "text-muted"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
          {current.hasPeriod && (
            <div className="flex items-end gap-2">
              <div>
                <Label htmlFor="date_from">From</Label>
                <Input
                  id="date_from"
                  type="date"
                  value={period.date_from ?? ""}
                  onChange={(e) => setPeriod({ ...period, date_from: e.target.value || undefined })}
                />
              </div>
              <div>
                <Label htmlFor="date_to">To</Label>
                <Input
                  id="date_to"
                  type="date"
                  value={period.date_to ?? ""}
                  onChange={(e) => setPeriod({ ...period, date_to: e.target.value || undefined })}
                />
              </div>
            </div>
          )}
        </div>

        {badPeriod && current.hasPeriod && <p className="text-sm text-danger">The start date is after the end date.</p>}
        {downloadError && <p className="text-sm text-danger">{downloadError}</p>}

        {!(badPeriod && current.hasPeriod) && (
          <>
            {kind === "projects" && <ProjectsReportView />}
            {kind === "inventory" && <InventoryReportView period={period} />}
            {kind === "procurement" && <ProcurementReportView period={period} />}
            {kind === "expenses" && <ExpenseReportView period={period} />}
          </>
        )}
      </div>
    </AppShell>
  );
}

function Table({ head, children, empty }: { head: string[]; children: ReactNode; empty: boolean }) {
  if (empty) return <Card className="text-center text-sm text-muted">Nothing to report for this selection.</Card>;
  return (
    <Card className="overflow-x-auto p-0">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
            {head.map((h) => (
              <th key={h} className="px-4 py-3 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </Card>
  );
}

function Stat({ label: text, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="text-xs uppercase tracking-wide text-muted">{text}</div>
      <div className="text-xl font-semibold text-ink">{value}</div>
    </Card>
  );
}

const td = "px-4 py-3";

function ProjectsReportView() {
  const query = useReport<ProjectReport>("projects", {});
  if (query.isLoading) return <TableSkeleton />;
  if (query.isError || !query.data) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const data = query.data;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Total budget" value={formatCurrency(data.total_budget)} />
        <Stat label="Committed (POs)" value={formatCurrency(data.total_committed)} />
        <Stat label="Spent (expenses)" value={formatCurrency(data.total_actual)} />
      </div>
      <Table
        empty={data.rows.length === 0}
        head={["Project", "Status", "Progress", "Budget", "Spent", "Forecast", "Variance", "Schedule", "Health", "Tasks"]}
      >
        {data.rows.map((r) => {
          const over = Number(r.expected_variance) > 0;
          return (
            <tr key={r.project_id} className="border-b border-border last:border-0">
              <td className={`${td} font-medium text-ink`}>
                {r.name} <span className="text-xs text-muted">{r.code}</span>
              </td>
              <td className={`${td} capitalize`}>{label(r.status)}</td>
              <td className={td}>{r.progress_percent}%</td>
              <td className={td}>{formatCurrency(r.budget)}</td>
              <td className={td}>{formatCurrency(r.actual)}</td>
              <td className={td}>{formatCurrency(r.forecast)}</td>
              <td className={`${td} ${over ? "text-danger" : "text-success"}`}>
                {over ? "+" : ""}
                {formatCurrency(r.expected_variance)}
              </td>
              <td className={td}>
                {r.schedule_variance_days === null
                  ? "—"
                  : r.schedule_variance_days > 0
                    ? `${r.schedule_variance_days}d behind`
                    : "on track"}
              </td>
              <td className={td}>{r.health_score ?? "—"}</td>
              <td className={td}>
                {r.open_tasks} open{r.overdue_tasks > 0 && <span className="text-danger">, {r.overdue_tasks} overdue</span>}
              </td>
            </tr>
          );
        })}
      </Table>
      <p className="text-xs text-muted">
        As of {data.as_of}. Forecast and variance use the same calculation as each project&apos;s Costs tab; before
        any progress is recorded, the forecast is just what&apos;s committed plus spent.
      </p>
    </div>
  );
}

function InventoryReportView({ period }: { period: Period }) {
  const query = useReport<InventoryReport>("inventory", period);
  if (query.isLoading) return <TableSkeleton />;
  if (query.isError || !query.data) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const data = query.data;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Materials" value={String(data.rows.length)} />
        <Stat label="Low stock" value={String(data.low_stock_count)} />
        <Stat label="Out of stock" value={String(data.out_of_stock_count)} />
      </div>
      <Table empty={data.rows.length === 0} head={["Material", "SKU", "On hand now", "Reorder at", "Status", "Received", "Issued"]}>
        {data.rows.map((r) => (
          <tr key={r.material_id} className="border-b border-border last:border-0">
            <td className={`${td} font-medium text-ink`}>{r.name}</td>
            <td className={`${td} text-muted`}>{r.sku}</td>
            <td className={td}>
              {r.on_hand} {r.unit}
            </td>
            <td className={td}>{r.reorder_point}</td>
            <td className={`${td} ${r.stock_status === "ok" ? "text-success" : r.stock_status === "low" ? "text-warning" : "text-danger"}`}>
              {r.stock_status === "ok" ? "OK" : r.stock_status === "low" ? "Low" : "Out"}
            </td>
            <td className={td}>{r.received}</td>
            <td className={td}>{r.issued}</td>
          </tr>
        ))}
      </Table>
      <p className="text-xs text-muted">
        &ldquo;On hand&rdquo; is always the current balance. &ldquo;Received&rdquo; (stock-in and goods receipts) and
        &ldquo;Issued&rdquo; (stock-out and project allocations) cover the selected period, in UTC days. Transfers
        between warehouses aren&apos;t counted in either.
      </p>
    </div>
  );
}

function ProcurementReportView({ period }: { period: Period }) {
  const query = useReport<ProcurementReport>("procurement", period);
  if (query.isLoading) return <TableSkeleton />;
  if (query.isError || !query.data) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const data = query.data;
  const statuses = Object.keys(data.po_count_by_status);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-ink">Purchase orders by status</h3>
          {statuses.length === 0 && <p className="text-sm text-muted">None in this period.</p>}
          <ul className="space-y-1 text-sm">
            {statuses.map((s) => (
              <li key={s} className="flex justify-between">
                <span className="capitalize">{label(s)}</span>
                <span>
                  {data.po_count_by_status[s]} · {formatCurrency(data.po_value_by_status[s])}
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-ink">Material requests by status</h3>
          {Object.keys(data.material_requests_by_status).length === 0 && (
            <p className="text-sm text-muted">None in this period.</p>
          )}
          <ul className="space-y-1 text-sm">
            {Object.entries(data.material_requests_by_status).map(([s, n]) => (
              <li key={s} className="flex justify-between">
                <span className="capitalize">{label(s)}</span>
                <span>{n}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
      <Table empty={data.rows.length === 0} head={["Supplier", "POs", "Ordered", "Received"]}>
        {data.rows.map((r) => (
          <tr key={r.supplier_id} className="border-b border-border last:border-0">
            <td className={`${td} font-medium text-ink`}>{r.supplier_name}</td>
            <td className={td}>{r.po_count}</td>
            <td className={td}>{formatCurrency(r.ordered_amount)}</td>
            <td className={td}>{formatCurrency(r.received_amount)}</td>
          </tr>
        ))}
      </Table>
      <p className="text-xs text-muted">POs and requests are included by the date they were created (UTC).</p>
    </div>
  );
}

function ExpenseReportView({ period }: { period: Period }) {
  const query = useReport<ExpenseReport>("expenses", period);
  if (query.isLoading) return <TableSkeleton />;
  if (query.isError || !query.data) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const data = query.data;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Total spent" value={formatCurrency(data.total_amount)} />
        {Object.entries(data.by_category)
          .sort((a, b) => Number(b[1]) - Number(a[1]))
          .slice(0, 2)
          .map(([category, amount]) => (
            <Stat key={category} label={category} value={formatCurrency(amount)} />
          ))}
      </div>
      <Table empty={data.rows.length === 0} head={["Project", "Category", "Entries", "Amount"]}>
        {data.rows.map((r) => (
          <tr key={`${r.project_id}-${r.category}`} className="border-b border-border last:border-0">
            <td className={`${td} font-medium text-ink`}>{r.project_name}</td>
            <td className={td}>{r.category}</td>
            <td className={td}>{r.expense_count}</td>
            <td className={td}>{formatCurrency(r.amount)}</td>
          </tr>
        ))}
      </Table>
      <p className="text-xs text-muted">Expenses are included by their expense date.</p>
    </div>
  );
}
