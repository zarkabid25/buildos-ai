import type { ReactNode } from "react";

export function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
      <div className="flex items-center justify-between">
        <h3 className="text-[17px] font-medium text-[var(--bo-text)]">{title}</h3>
      </div>
      {subtitle && <p className="mt-1 text-sm text-[var(--bo-text-muted)]">{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </div>
  );
}

// The honest missing-data state: this portal doesn't have subscriptions/CRM/
// marketplace data yet, so these charts can't be real. Matches the chart card's
// shell rather than being omitted outright or faked with placeholder numbers.
export function UnavailableChartCard({ title, reason }: { title: string; reason: string }) {
  return (
    <ChartCard title={title}>
      <div className="flex h-[220px] flex-col items-center justify-center rounded-lg border border-dashed border-[var(--bo-border)] text-center">
        <p className="text-sm font-medium text-[var(--bo-text-secondary)]">Not available yet</p>
        <p className="mt-1 max-w-xs text-xs text-[var(--bo-text-muted)]">{reason}</p>
      </div>
    </ChartCard>
  );
}
