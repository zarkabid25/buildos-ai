"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import { projectCreateSchema, type ProjectCreateInput } from "@/lib/project-schema";
import { useCreateProject, useProjects } from "@/lib/use-projects";
import { formatCurrency, STATUS_CLASSES, STATUS_LABELS } from "@/lib/utils";

export default function ProjectsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProjectCreateInput>({ resolver: zodResolver(projectCreateSchema) });

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  async function onSubmit(values: ProjectCreateInput) {
    setFormError(null);
    try {
      await createProject.mutateAsync(values);
      reset();
      setShowForm(false);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create project");
    }
  }

  if (authLoading || !user) return null;

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-ink">Projects</h1>
            <p className="text-muted">All construction projects across your company.</p>
          </div>
          <Button onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "+ New Project"}
          </Button>
        </div>

        {showForm && (
          <Card>
            <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="name">Project name</Label>
                <Input id="name" {...register("name")} />
                {errors.name && <p className="mt-1 text-xs text-danger">{errors.name.message}</p>}
              </div>
              <div>
                <Label htmlFor="code">Project code</Label>
                <Input id="code" placeholder="e.g. PRJ-001" {...register("code")} />
                {errors.code && <p className="mt-1 text-xs text-danger">{errors.code.message}</p>}
              </div>
              <div>
                <Label htmlFor="client_name">Client</Label>
                <Input id="client_name" {...register("client_name")} />
              </div>
              <div>
                <Label htmlFor="location">Location</Label>
                <Input id="location" {...register("location")} />
              </div>
              <div>
                <Label htmlFor="start_date">Start date</Label>
                <Input id="start_date" type="date" {...register("start_date")} />
              </div>
              <div>
                <Label htmlFor="end_date">End date</Label>
                <Input id="end_date" type="date" {...register("end_date")} />
              </div>
              <div>
                <Label htmlFor="budget">Budget (PKR)</Label>
                <Input id="budget" type="number" step="0.01" {...register("budget")} />
              </div>
              {formError && <p className="col-span-full text-sm text-danger">{formError}</p>}
              <div className="col-span-full">
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Creating..." : "Create project"}
                </Button>
              </div>
            </form>
          </Card>
        )}

        {isLoading && <p className="text-sm text-muted">Loading projects...</p>}

        {!isLoading && projects && projects.length === 0 && (
          <Card className="text-center text-sm text-muted">
            No projects yet. Create your first project to start tracking BOQ, inventory and cost.
          </Card>
        )}

        {!isLoading && projects && projects.length > 0 && (
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3 font-medium">Project</th>
                  <th className="px-4 py-3 font-medium">Client</th>
                  <th className="px-4 py-3 font-medium">Progress</th>
                  <th className="px-4 py-3 font-medium">Budget</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((project) => (
                  <tr key={project.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3">
                      <Link href={`/projects/${project.id}`} className="font-medium text-ink hover:text-primary">
                        {project.name}
                      </Link>
                      <div className="text-xs text-muted">{project.code}</div>
                    </td>
                    <td className="px-4 py-3 text-muted">{project.client_name ?? "—"}</td>
                    <td className="px-4 py-3 text-ink">{project.progress_percent}%</td>
                    <td className="px-4 py-3 text-ink">{formatCurrency(project.budget)}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[project.status]}`}
                      >
                        {STATUS_LABELS[project.status]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
