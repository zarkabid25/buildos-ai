"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";
import { useProject } from "@/lib/use-projects";
import { formatCurrency, STATUS_CLASSES, STATUS_LABELS } from "@/lib/utils";

const TABS = ["Overview", "BOQ", "Tasks", "Procurement", "Inventory", "Expenses", "Reports", "Documents"];

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const { data: project, isLoading, isError } = useProject(id);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  return (
    <AppShell>
      {isLoading && <p className="text-sm text-muted">Loading project...</p>}
      {isError && <p className="text-sm text-danger">Could not load this project.</p>}

      {project && (
        <div className="space-y-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-ink">{project.name}</h1>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[project.status]}`}
              >
                {STATUS_LABELS[project.status]}
              </span>
            </div>
            <p className="text-muted">
              {project.client_name ?? "No client set"}
              {project.location ? ` — ${project.location}` : ""}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Card>
              <div className="text-xs uppercase text-muted">Progress</div>
              <div className="text-xl font-semibold text-ink">{project.progress_percent}%</div>
            </Card>
            <Card>
              <div className="text-xs uppercase text-muted">Budget</div>
              <div className="text-xl font-semibold text-ink">{formatCurrency(project.budget)}</div>
            </Card>
            <Card>
              <div className="text-xs uppercase text-muted">Start</div>
              <div className="text-xl font-semibold text-ink">{project.start_date ?? "—"}</div>
            </Card>
            <Card>
              <div className="text-xs uppercase text-muted">End</div>
              <div className="text-xl font-semibold text-ink">{project.end_date ?? "—"}</div>
            </Card>
          </div>

          <div className="flex gap-1 border-b border-border">
            {TABS.map((tab, i) => (
              <div
                key={tab}
                className={`px-3 py-2 text-sm ${
                  i === 0 ? "border-b-2 border-primary font-medium text-ink" : "text-muted"
                }`}
              >
                {tab}
              </div>
            ))}
          </div>

          <Card>
            <p className="text-sm text-muted">
              {project.description ?? "No description yet."} BOQ, tasks, procurement and the rest
              of the project workflow land in upcoming builds.
            </p>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
