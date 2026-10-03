"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { EmptyState, QueryView } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import type { TaskStatus } from "@/lib/task-types";
import { useProjects } from "@/lib/use-projects";
import { useCompanyTasks, useSetTaskStatus } from "@/lib/use-tasks";
import { localToday } from "@/lib/utils";

const STATUSES: TaskStatus[] = ["todo", "in_progress", "blocked", "done"];
const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "To do",
  in_progress: "In progress",
  blocked: "Blocked",
  done: "Done",
};

export default function TasksPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [mine, setMine] = useState(false);
  const [status, setStatus] = useState<TaskStatus | "">("");
  const [projectId, setProjectId] = useState("");
  const { data: projects } = useProjects();
  const tasksQuery = useCompanyTasks({ mine, status: status || undefined, projectId: projectId || undefined });
  const setTaskStatus = useSetTaskStatus();

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;
  const today = localToday();
  const selectClass = "h-9 rounded-md border border-border bg-surface px-2 text-sm";

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Tasks</h1>
          <p className="text-muted">Every task across your projects. Open work first, soonest due at the top.</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-md border border-border bg-surface p-0.5 text-sm">
            {[
              { label: "All tasks", value: false },
              { label: "Assigned to me", value: true },
            ].map((opt) => (
              <button
                key={opt.label}
                onClick={() => setMine(opt.value)}
                className={`rounded px-3 py-1 ${mine === opt.value ? "bg-primary text-white" : "text-muted hover:text-ink"}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <select aria-label="Status" className={selectClass} value={status} onChange={(e) => setStatus(e.target.value as TaskStatus | "")}>
            <option value="">Any status</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
          <select aria-label="Project" className={selectClass} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">All projects</option>
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <QueryView
          query={tasksQuery}
          isEmpty={(list) => list.length === 0}
          empty={
            <EmptyState
              title={mine || status || projectId ? "No tasks match these filters" : "No tasks yet"}
              hint="Tasks are added from a project's Tasks tab."
            />
          }
        >
          {(tasks) => (
            <Card className="overflow-x-auto p-0">
              <table className="w-full whitespace-nowrap text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                    <th className="px-4 py-3 font-medium">Task</th>
                    <th className="px-4 py-3 font-medium">Project</th>
                    <th className="px-4 py-3 font-medium">Assignee</th>
                    <th className="px-4 py-3 font-medium">Due</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((t) => {
                    const overdue = t.status !== "done" && !!t.due_date && t.due_date < today;
                    return (
                      <tr key={t.id} className="border-b border-border last:border-0">
                        <td className="px-4 py-3 font-medium text-ink">{t.title}</td>
                        <td className="px-4 py-3">
                          <Link href={`/projects/${t.project_id}`} className="text-primary hover:underline">
                            {t.project_name}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-muted">{t.assignee_name ?? "Unassigned"}</td>
                        <td className={`px-4 py-3 ${overdue ? "font-medium text-danger" : "text-muted"}`}>
                          {t.due_date ?? "—"}
                          {overdue && " (overdue)"}
                        </td>
                        <td className="px-4 py-3">
                          <select
                            aria-label={`Status of ${t.title}`}
                            className="h-8 rounded-md border border-border bg-surface px-2 text-xs"
                            value={t.status}
                            disabled={setTaskStatus.isPending}
                            onChange={(e) =>
                              setTaskStatus.mutate({ projectId: t.project_id, taskId: t.id, status: e.target.value as TaskStatus })
                            }
                          >
                            {STATUSES.map((s) => (
                              <option key={s} value={s}>
                                {STATUS_LABELS[s]}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>
          )}
        </QueryView>
      </div>
    </AppShell>
  );
}
