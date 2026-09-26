import Link from "next/link";

import type { Insight } from "@/lib/use-ai";

const SEVERITY_CLASSES: Record<Insight["severity"], string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-gray-100 text-gray-700",
};

export function InsightsList({ insights, limit }: { insights: Insight[]; limit?: number }) {
  const shown = limit ? insights.slice(0, limit) : insights;

  if (shown.length === 0) {
    return <p className="text-sm text-muted">Nothing needs attention right now.</p>;
  }

  return (
    <ul className="divide-y divide-border">
      {shown.map((insight, i) => (
        <li key={`${insight.title}-${i}`} className="flex items-start gap-3 py-3">
          <span
            className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_CLASSES[insight.severity]}`}
          >
            {insight.severity}
          </span>
          <div className="min-w-0">
            <div className="text-sm font-medium text-ink">
              {insight.project_id ? (
                <Link href={`/projects/${insight.project_id}`} className="hover:text-primary">
                  {insight.title}
                </Link>
              ) : (
                insight.title
              )}
            </div>
            <div className="text-xs text-muted">{insight.detail}</div>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function RulesNote() {
  return (
    <p className="text-xs text-muted">
      Generated from your data by fixed rules and thresholds — not written by an AI model.
    </p>
  );
}
