"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import {
  useAddDependency,
  useProjectSchedule,
  useRemoveDependency,
} from "@/lib/use-tasks";
import type { Task } from "@/lib/task-types";

const STATUS_BAR_CLASSES: Record<Task["status"], string> = {
  todo: "bg-gray-300",
  in_progress: "bg-primary",
  blocked: "bg-danger",
  done: "bg-success",
};

const TASK_STATUS_LABELS: Record<Task["status"], string> = {
  todo: "To do",
  in_progress: "In progress",
  blocked: "Blocked",
  done: "Done",
};

function dayIndex(dateStr: string, timelineStart: number): number {
  return Math.floor((new Date(dateStr + "T00:00:00").getTime() - timelineStart) / 86_400_000);
}

export function SchedulePanel({ projectId }: { projectId: string }) {
  const { data: schedule, isLoading } = useProjectSchedule(projectId);
  const addDependency = useAddDependency(projectId);
  const removeDependency = useRemoveDependency(projectId);
  const [depForm, setDepForm] = useState<{ taskId: string; dependsOn: string }>({ taskId: "", dependsOn: "" });
  const [error, setError] = useState<string | null>(null);

  const timeline = useMemo(() => {
    if (!schedule) return null;
    const dated = schedule.tasks.filter((t) => t.start_date || t.due_date);
    const dates = dated.flatMap((t) => [t.start_date, t.due_date].filter(Boolean) as string[]);
    const milestoneDates = schedule.milestones.map((m) => m.due_date).filter(Boolean) as string[];
    const all = [...dates, ...milestoneDates];
    if (all.length === 0) return null;
    const times = all.map((d) => new Date(d + "T00:00:00").getTime());
    const start = Math.min(...times);
    const end = Math.max(...times);
    const totalDays = Math.max(1, Math.round((end - start) / 86_400_000) + 1);
    return { start, totalDays };
  }, [schedule]);

  async function handleAddDependency() {
    setError(null);
    if (!depForm.taskId || !depForm.dependsOn || depForm.taskId === depForm.dependsOn) return;
    try {
      await addDependency.mutateAsync({ taskId: depForm.taskId, dependsOnTaskId: depForm.dependsOn });
      setDepForm({ taskId: "", dependsOn: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add that dependency");
    }
  }

  if (isLoading) return <p className="text-sm text-muted">Loading schedule...</p>;
  if (!schedule) return null;

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-1 text-sm font-semibold text-ink">Schedule variance</h2>
        <p className="text-sm text-ink">{schedule.variance_note}</p>
        {schedule.schedule_variance_percent !== null && (
          <p className="mt-1 text-xs text-muted">
            {schedule.schedule_variance_percent > 0 ? "+" : ""}
            {schedule.schedule_variance_percent} percentage point(s) vs. elapsed time, computed from the
            project&apos;s start/end dates and reported progress.
          </p>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-ink">Timeline</h2>
        {!timeline && (
          <p className="text-sm text-muted">
            Add start/due dates to tasks (or a due date to a milestone) to see a timeline here.
          </p>
        )}
        {timeline && (
          <div className="space-y-2">
            {schedule.tasks
              .filter((t) => t.start_date || t.due_date)
              .map((task) => {
                const startIdx = task.start_date ? dayIndex(task.start_date, timeline.start) : dayIndex(task.due_date!, timeline.start);
                const endIdx = task.due_date ? dayIndex(task.due_date, timeline.start) : startIdx;
                const left = (startIdx / timeline.totalDays) * 100;
                const width = Math.max(2, ((endIdx - startIdx + 1) / timeline.totalDays) * 100);
                return (
                  <div key={task.id} className="flex items-center gap-3 text-xs">
                    <div className="w-32 shrink-0 truncate text-ink" title={task.title}>
                      {task.title}
                    </div>
                    <div className="relative h-5 flex-1 rounded bg-gray-50">
                      <div
                        className={`absolute h-5 rounded ${STATUS_BAR_CLASSES[task.status]}`}
                        style={{ left: `${left}%`, width: `${width}%` }}
                        title={`${TASK_STATUS_LABELS[task.status]}${task.start_date ? ` · ${task.start_date}` : ""}${task.due_date ? ` → ${task.due_date}` : ""}`}
                      />
                    </div>
                  </div>
                );
              })}
            {schedule.milestones
              .filter((m) => m.due_date)
              .map((m) => {
                const idx = dayIndex(m.due_date!, timeline.start);
                const left = (idx / timeline.totalDays) * 100;
                return (
                  <div key={m.id} className="flex items-center gap-3 text-xs">
                    <div className="w-32 shrink-0 truncate text-ink" title={m.name}>
                      ◆ {m.name}
                    </div>
                    <div className="relative h-5 flex-1 rounded bg-gray-50">
                      <div
                        className={`absolute top-0.5 h-4 w-4 rotate-45 ${m.is_completed ? "bg-success" : "bg-warning"}`}
                        style={{ left: `calc(${left}% - 8px)` }}
                        title={`${m.name} · ${m.due_date}`}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-ink">Task dependencies</h2>
        <div className="mb-4 flex flex-wrap items-end gap-2">
          <select
            className="h-9 rounded-md border border-border bg-surface px-2 text-sm"
            value={depForm.taskId}
            onChange={(e) => setDepForm({ ...depForm, taskId: e.target.value })}
          >
            <option value="">Task...</option>
            {schedule.tasks.map((t) => (
              <option key={t.id} value={t.id}>{t.title}</option>
            ))}
          </select>
          <span className="text-xs text-muted">depends on</span>
          <select
            className="h-9 rounded-md border border-border bg-surface px-2 text-sm"
            value={depForm.dependsOn}
            onChange={(e) => setDepForm({ ...depForm, dependsOn: e.target.value })}
          >
            <option value="">Task...</option>
            {schedule.tasks.map((t) => (
              <option key={t.id} value={t.id}>{t.title}</option>
            ))}
          </select>
          <Button onClick={handleAddDependency} disabled={addDependency.isPending}>
            Add
          </Button>
        </div>
        {error && <p className="mb-2 text-sm text-danger">{error}</p>}

        {schedule.tasks.every((t) => t.depends_on.length === 0) ? (
          <p className="text-sm text-muted">No dependencies set.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {schedule.tasks
              .filter((t) => t.depends_on.length > 0)
              .map((t) => (
                <li key={t.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-ink">{t.title} depends on:</span>
                  {t.depends_on.map((depId) => {
                    const dep = schedule.tasks.find((x) => x.id === depId);
                    return (
                      <span
                        key={depId}
                        className="flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-ink"
                      >
                        {dep?.title ?? depId}
                        <button
                          className="text-muted hover:text-danger"
                          onClick={() => removeDependency.mutate({ taskId: t.id, dependsOnTaskId: depId })}
                        >
                          ×
                        </button>
                      </span>
                    );
                  })}
                </li>
              ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
