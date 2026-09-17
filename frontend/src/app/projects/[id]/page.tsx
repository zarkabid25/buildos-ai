"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth-context";
import { useProject } from "@/lib/use-projects";
import {
  useAcceptAiBoq,
  useBoqItems,
  useBoqSummary,
  useCreateBoqItem,
  useDeleteBoqItem,
  useGenerateAiBoq,
} from "@/lib/use-boq";
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
import { formatCurrency, STATUS_CLASSES, STATUS_LABELS } from "@/lib/utils";
import type { TaskStatus } from "@/lib/task-types";
import type { BoqAiGeneratedItem } from "@/lib/boq-types";

const TABS = ["Overview", "BOQ", "Tasks", "Milestones", "Members"] as const;
type Tab = (typeof TABS)[number];

const TASK_STATUS_OPTIONS: TaskStatus[] = ["todo", "in_progress", "blocked", "done"];

function HealthBar({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
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

  const { data: project, isLoading, isError } = useProject(id);
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

          <div className="flex gap-1 border-b border-border">
            {TABS.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-2 text-sm ${
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
                <h2 className="mb-3 text-sm font-semibold text-ink">Project Health</h2>
                <div className="space-y-3">
                  <HealthBar label="Schedule" value={health?.schedule_score ?? null} />
                  <HealthBar label="Cost" value={health?.cost_score ?? null} />
                  <HealthBar label="Inventory" value={health?.inventory_score ?? null} />
                  <HealthBar label="Quality" value={health?.quality_score ?? null} />
                  <HealthBar label="Safety" value={health?.safety_score ?? null} />
                  <HealthBar label="Labor" value={health?.labor_score ?? null} />
                  <HealthBar label="Procurement" value={health?.procurement_score ?? null} />
                </div>
                <p className="mt-3 text-xs text-muted">
                  Scores marked &ldquo;no data&rdquo; need their source module (cost tracking,
                  inventory, daily reports...) built first — coming in later builds.
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
          {tab === "Milestones" && <MilestonesPanel projectId={id} milestones={milestones ?? []} />}
          {tab === "Members" && <MembersPanel members={members ?? []} />}
        </div>
      )}
    </AppShell>
  );
}

function TasksPanel({ projectId, tasks }: { projectId: string; tasks: import("@/lib/task-types").Task[] }) {
  const [title, setTitle] = useState("");
  const createTask = useCreateTask(projectId);
  const updateStatus = useUpdateTaskStatus(projectId);

  async function handleAdd() {
    if (!title.trim()) return;
    await createTask.mutateAsync({ title: title.trim() });
    setTitle("");
  }

  return (
    <Card>
      <div className="mb-4 flex gap-2">
        <Input
          placeholder="New task title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
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
                {task.priority} {task.due_date ? `· due ${task.due_date}` : ""}
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
    await createMilestone.mutateAsync({ name: name.trim() });
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

function BoqPanel({ projectId }: { projectId: string }) {
  const { data: items } = useBoqItems(projectId);
  const { data: summary } = useBoqSummary(projectId);
  const createItem = useCreateBoqItem(projectId);
  const deleteItem = useDeleteBoqItem(projectId);
  const generateAi = useGenerateAiBoq(projectId);
  const acceptAi = useAcceptAiBoq(projectId);

  const [form, setForm] = useState({ item_code: "", description: "", unit: "", quantity: "", rate: "" });
  const [draft, setDraft] = useState<BoqAiGeneratedItem[] | null>(null);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);

  async function handleAdd() {
    if (!form.item_code || !form.description || !form.unit) return;
    await createItem.mutateAsync({
      item_code: form.item_code,
      description: form.description,
      unit: form.unit,
      quantity: form.quantity || "0",
      rate: form.rate || "0",
    });
    setForm({ item_code: "", description: "", unit: "", quantity: "", rate: "" });
  }

  async function handleGenerate() {
    const res = await generateAi.mutateAsync({ project_type: "residential" });
    setDraft(res.items);
    setDisclaimer(res.disclaimer);
  }

  async function handleAcceptDraft() {
    if (!draft) return;
    await acceptAi.mutateAsync(draft);
    setDraft(null);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted">
          {summary ? `${summary.item_count} items · ${formatCurrency(summary.total_amount)} total` : ""}
        </div>
        <Button variant="secondary" onClick={handleGenerate} disabled={generateAi.isPending}>
          ✨ {generateAi.isPending ? "Generating..." : "Generate BOQ with AI"}
        </Button>
      </div>

      {draft && (
        <Card className="border-primary/40 bg-blue-50/40">
          <h3 className="mb-1 text-sm font-semibold text-ink">AI-generated draft — review before adding</h3>
          <p className="mb-3 text-xs text-muted">{disclaimer}</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-muted">
                <th className="py-1">Item</th>
                <th className="py-1">Description</th>
                <th className="py-1">Unit</th>
                <th className="py-1">Qty</th>
                <th className="py-1">Rate</th>
              </tr>
            </thead>
            <tbody>
              {draft.map((d) => (
                <tr key={d.item_code} className="border-t border-border/60">
                  <td className="py-1">{d.item_code}</td>
                  <td className="py-1">{d.description}</td>
                  <td className="py-1">{d.unit}</td>
                  <td className="py-1">{d.quantity}</td>
                  <td className="py-1">{d.rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 flex gap-2">
            <Button onClick={handleAcceptDraft} disabled={acceptAi.isPending}>
              {acceptAi.isPending ? "Adding..." : `Add all ${draft.length} items`}
            </Button>
            <Button variant="secondary" onClick={() => setDraft(null)}>
              Discard
            </Button>
          </div>
        </Card>
      )}

      <Card>
        <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
          <div>
            <Label htmlFor="boq_code">Item</Label>
            <Input id="boq_code" value={form.item_code} onChange={(e) => setForm({ ...form, item_code: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="boq_desc">Description</Label>
            <Input id="boq_desc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="boq_unit">Unit</Label>
            <Input id="boq_unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="boq_qty">Qty</Label>
            <Input id="boq_qty" type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="boq_rate">Rate</Label>
            <Input id="boq_rate" type="number" value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} />
          </div>
          <div className="flex items-end">
            <Button onClick={handleAdd} disabled={createItem.isPending} className="w-full">
              Add item
            </Button>
          </div>
        </div>

        {(!items || items.length === 0) && <p className="text-sm text-muted">No BOQ items yet.</p>}

        {items && items.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-2 py-2">Item</th>
                <th className="px-2 py-2">Description</th>
                <th className="px-2 py-2">Unit</th>
                <th className="px-2 py-2">Qty</th>
                <th className="px-2 py-2">Rate</th>
                <th className="px-2 py-2">Amount</th>
                <th className="px-2 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-border last:border-0">
                  <td className="px-2 py-2">
                    {item.item_code}
                    {item.is_ai_generated && (
                      <span className="ml-1 rounded bg-blue-100 px-1 text-[10px] text-blue-700">AI</span>
                    )}
                  </td>
                  <td className="px-2 py-2">{item.description}</td>
                  <td className="px-2 py-2 text-muted">{item.unit}</td>
                  <td className="px-2 py-2">{item.quantity}</td>
                  <td className="px-2 py-2">{formatCurrency(item.rate)}</td>
                  <td className="px-2 py-2 font-medium">{formatCurrency(item.amount)}</td>
                  <td className="px-2 py-2 text-right">
                    <button
                      onClick={() => deleteItem.mutate(item.id)}
                      className="text-xs text-muted hover:text-danger"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
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
