"use client";

import { Card } from "@/components/ui/card";
import { useBoqVsActual } from "@/lib/use-boq";
import type { BoqLineStatus } from "@/lib/boq-types";
import { formatCurrency } from "@/lib/utils";

const STATUS_LABELS: Record<BoqLineStatus, string> = {
  not_tracked: "Not linked",
  not_started: "Not started",
  within_plan: "Within plan",
  over_plan: "Over plan",
};

const STATUS_CLASSES: Record<BoqLineStatus, string> = {
  not_tracked: "bg-gray-100 text-muted",
  not_started: "bg-gray-100 text-ink",
  within_plan: "bg-green-50 text-success",
  over_plan: "bg-red-50 text-danger",
};

export function BoqVsActualPanel({ projectId }: { projectId: string }) {
  const { data } = useBoqVsActual(projectId);
  if (!data || (data.lines.length === 0 && data.unplanned.length === 0)) return null;

  return (
    <Card>
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">BOQ vs actual</h3>
        <span className="text-xs text-muted">
          Tracked plan {formatCurrency(data.tracked_planned_total)} · Used so far {formatCurrency(data.actual_total)}
        </span>
      </div>
      <p className="mb-3 text-xs text-muted">{data.valuation_note}</p>

      {data.lines.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-2 py-2">Item</th>
                <th className="px-2 py-2">Material</th>
                <th className="px-2 py-2">Planned</th>
                <th className="px-2 py-2">Actual</th>
                <th className="px-2 py-2">Variance</th>
                <th className="px-2 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((line) => (
                <tr key={line.boq_item_id} className="border-b border-border last:border-0">
                  <td className="px-2 py-2">
                    {line.item_code} <span className="text-muted">{line.description}</span>
                  </td>
                  <td className="px-2 py-2 text-muted">{line.material_name ?? "—"}</td>
                  <td className="px-2 py-2">
                    {line.planned_quantity} {line.unit}
                  </td>
                  <td className="px-2 py-2">{line.actual_quantity !== null ? `${line.actual_quantity} ${line.unit}` : "—"}</td>
                  <td className="px-2 py-2">
                    {line.quantity_variance !== null
                      ? `${Number(line.quantity_variance) > 0 ? "+" : ""}${line.quantity_variance}${
                          line.variance_percent !== null ? ` (${line.variance_percent}%)` : ""
                        }`
                      : "—"}
                  </td>
                  <td className="px-2 py-2">
                    <span className={`rounded px-1.5 py-0.5 text-xs ${STATUS_CLASSES[line.status]}`}>
                      {STATUS_LABELS[line.status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data.unplanned.length > 0 && (
        <div className="mt-4">
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
            Used on this project but not in the BOQ
          </h4>
          <ul className="text-sm">
            {data.unplanned.map((u) => (
              <li key={u.material_id}>
                {u.material_name}: {u.actual_quantity} {u.unit}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
