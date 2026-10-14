import type { ReactNode } from "react";

// White outer card + pale-lavender inset panel + white footer, per
// docs/design-system-admin-portal.md. Trend is optional and only ever shown when
// a real comparison exists -- never fabricated.
export function MetricCard({
  icon,
  label,
  value,
  trend,
  dateRange,
  detailsHref,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  trend?: { direction: "up" | "down"; text: string } | null;
  dateRange: string;
  detailsHref?: string;
}) {
  return (
    <div className="overflow-hidden rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] shadow-[var(--bo-shadow-card)]">
      <div className="m-1 rounded-[11px] bg-[var(--bo-kpi-surface)] p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-[15px] font-medium text-[var(--bo-text-secondary)]">
            {icon}
            <span>{label}</span>
          </div>
          <span className="text-xs font-medium text-[var(--bo-text-muted)]">
            {trend ? `${trend.direction === "up" ? "↑" : "↓"} ${trend.text}` : "—"}
          </span>
        </div>
        <p className="bo-tabular mt-3 text-[32px] font-medium leading-tight tracking-[-0.025em] text-[var(--bo-text)]">
          {value}
        </p>
      </div>
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-xs text-[var(--bo-text-muted)]">{dateRange}</span>
        {detailsHref && (
          <a
            href={detailsHref}
            className="rounded-md bg-[var(--bo-nav-active)] px-2.5 py-1 text-xs font-medium text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]"
          >
            View details
          </a>
        )}
      </div>
    </div>
  );
}
