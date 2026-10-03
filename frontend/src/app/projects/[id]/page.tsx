"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { BoqPanel } from "@/components/boq-panel";
import { CostsPanel } from "@/components/costs-panel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ErrorState, Skeleton, TableSkeleton } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import { useProject } from "@/lib/use-projects";
import {
  useCreateMilestone,
  useCreateTask,
  useMilestones,
  useProjectHealth,
  useProjectMembers,
  useTasks,
  useToggleMilestone,
  useUpdateTaskStatus,
} from "@/lib/use-tasks";
import { DailyReportsPanel } from "@/components/daily-reports-panel";
import { SchedulePanel } from "@/components/schedule-panel";
import { attempt, formatCurrency, STATUS_CLASSES, STATUS_LABELS } from "@/lib/utils";
import type { TaskStatus } from "@/lib/task-types";

const TABS = ["Overview", "BOQ", "Tasks", "Schedule", "Milestones", "Members", "Costs", "Reports"] as const;
type Tab = (typeof TABS)[number];

const TASK_STATUS_OPTIONS: TaskStatus[] = ["todo", "in_progress", "blocked", "done"];

function HealthBar({ label, value, basis }: { label: string; value: number | null; basis?: string }) {
  return (
    <div title={basis}>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="text-ink">{value === null ? "no data" : `${value}`}</span>
      </div>
      <div className="h-2 rounded-full bg-gray-100">
        <div
          className="h-2 rounded-full bg-primary"
          style={{ width: value === null ? "0%" : `${value}%` }}
        />
      </div>
    </div>
  );
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("Overview");

  const { data: project, isLoading, isError, error, refetch } = useProject(id);
  const { data: health } = useProjectHealth(id);
  const { data: tasks } = useTasks(id);
  const { data: milestones } = useMilestones(id);
  const { data: members } = useProjectMembers(id);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  return (
    <AppShell>
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <TableSkeleton rows={6} />
        </div>
      )}
      {isError && <ErrorState error={error} onRetry={() => refetch()} />}

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
              {health?.is_at_risk && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                  At risk
                </span>
              )}
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

          <div className="flex gap-1 overflow-x-auto border-b border-border">
            {TABS.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`shrink-0 whitespace-nowrap px-3 py-2 text-sm ${
                  tab === t ? "border-b-2 border-primary font-medium text-ink" : "text-muted"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === "Overview" && (
            <div className="space-y-4">
              <Card>
                <div className="mb-3 flex items-baseline justify-between">
                  <h2 className="text-sm font-semibold text-ink">Project Health</h2>
                  <span className="text-sm text-ink">
                    {health?.overall_score != null ? `Overall ${health.overall_score}/100` : "Overall: no data"}
                  </span>
                </div>
                <div className="space-y-3">
                  <HealthBar label="Schedule" value={health?.schedule_score ?? null} basis={health?.basis.schedule} />
                  <HealthBar label="Cost" value={health?.cost_score ?? null} basis={health?.basis.cost} />
                  <HealthBar label="Inventory" value={health?.inventory_score ?? null} basis={health?.basis.inventory} />
                  <HealthBar label="Quality" value={health?.quality_score ?? null} />
                  <HealthBar label="Safety" value={health?.safety_score ?? null} />
                  <HealthBar label="Labor" value={health?.labor_score ?? null} />
                  <HealthBar label="Procurement" value={health?.procurement_score ?? null} />
                </div>
                <p className="mt-3 text-xs text-muted">
                  Overall is the average of the scored bars. Cost is scored once progress is recorded;
                  inventory once BOQ lines are linked to materials. Quality, safety, labor and
                  procurement have no scoring data yet. Hover a bar to see how it was worked out.
                </p>
              </Card>
              <Card>
                <p className="text-sm text-muted">
                  {project.description ?? "No description yet."}
                </p>
              </Card>
            </div>
          )}

          {tab === "BOQ" && <BoqPanel projectId={id} />}
          {tab === "Tasks" && <TasksPanel projectId={id} tasks={tasks ?? []} />}
          {tab === "Schedule" && <SchedulePanel projectId={id} />}
          {tab === "Milestones" && <MilestonesPanel projectId={id} milestones={milestones ?? []} />}
          {tab === "Members" && <MembersPanel members={members ?? []} />}
          {tab === "Costs" && <CostsPanel projectId={id} />}
          {tab === "Reports" && <DailyReportsPanel projectId={id} />}
        </div>
      )}
    </AppShell>
  );
}

function TasksPanel({ projectId, tasks }: { projectId: string; tasks: import("@/lib/task-types").Task[] }) {
  const [title, setTitle] = useState("");
  const [startDate, setStartDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const createTask = useCreateTask(projectId);
  const updateStatus = useUpdateTaskStatus(projectId);

  async function handleAdd() {
    if (!title.trim()) return;
    if (!(await attempt(createTask.mutateAsync({
      title: title.trim(),
      start_date: startDate || undefined,
      due_date: dueDate || undefined,
    })))) return;
    setTitle("");
    setStartDate("");
    setDueDate("");
  }

  return (
    <Card>
      <div className="mb-4 flex flex-wrap gap-2">
        <Input
          placeholder="New task title"
          className="flex-1"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
        />
        <Input
          type="date"
          title="Start date"
          className="w-40"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
        />
        <Input
          type="date"
          title="Due date"
          className="w-40"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
        />
        <Button onClick={handleAdd} disabled={createTask.isPending}>
          Add
        </Button>
      </div>
      {tasks.length === 0 && <p className="text-sm text-muted">No tasks yet.</p>}
      <ul className="divide-y divide-border">
        {tasks.map((task) => (
          <li key={task.id} className="flex items-center justify-between py-2">
            <div>
              <div className="text-sm text-ink">{task.title}</div>
              <div className="text-xs text-muted">
                {task.priority}
                {task.start_date ? ` · starts ${task.start_date}` : ""}
                {task.due_date ? ` · due ${task.due_date}` : ""}
              </div>
            </div>
            <select
              value={task.status}
              onChange={(e) =>
                updateStatus.mutate({ taskId: task.id, status: e.target.value as TaskStatus })
              }
              className="h-8 rounded-md border border-border bg-surface px-2 text-xs"
            >
              {TASK_STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function MilestonesPanel({
  projectId,
  milestones,
}: {
  projectId: string;
  milestones: import("@/lib/task-types").Milestone[];
}) {
  const [name, setName] = useState("");
  const createMilestone = useCreateMilestone(projectId);
  const toggleMilestone = useToggleMilestone(projectId);

  async function handleAdd() {
    if (!name.trim()) return;
    if (!(await attempt(createMilestone.mutateAsync({ name: name.trim() })))) return;
    setName("");
  }

  return (
    <Card>
      <div className="mb-4 flex gap-2">
        <Input
          placeholder="New milestone"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
        />
        <Button onClick={handleAdd} disabled={createMilestone.isPending}>
          Add
        </Button>
      </div>
      {milestones.length === 0 && <p className="text-sm text-muted">No milestones yet.</p>}
      <ul className="divide-y divide-border">
        {milestones.map((m) => (
          <li key={m.id} className="flex items-center gap-3 py-2">
            <input
              type="checkbox"
              checked={m.is_completed}
              onChange={(e) =>
                toggleMilestone.mutate({ milestoneId: m.id, is_completed: e.target.checked })
              }
            />
            <span className={`text-sm ${m.is_completed ? "text-muted line-through" : "text-ink"}`}>
              {m.name}
            </span>
            {m.due_date && <span className="text-xs text-muted">due {m.due_date}</span>}
          </li>
        ))}
      </ul>
    </Card>
  );
}

function MembersPanel({ members }: { members: import("@/lib/task-types").ProjectMember[] }) {
  return (
    <Card>
      {members.length === 0 && (
        <p className="text-sm text-muted">No members assigned to this project yet.</p>
      )}
      <ul className="divide-y divide-border">
        {members.map((m) => (
          <li key={m.id} className="flex items-center justify-between py-2">
            <div>
              <div className="text-sm text-ink">{m.user.full_name}</div>
              <div className="text-xs text-muted">{m.user.email}</div>
            </div>
            <span className="text-xs text-muted">{m.user.role.replace("_", " ")}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

