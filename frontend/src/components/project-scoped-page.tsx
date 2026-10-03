"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { EmptyState, QueryView } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import { useProjects } from "@/lib/use-projects";

const REMEMBERED_PROJECT = "buildos_selected_project";

function readRemembered(): string | null {
  try {
    return window.localStorage.getItem(REMEMBERED_PROJECT);
  } catch {
    return null;
  }
}

/**
 * A sidebar page for one project-level module (BOQ, schedule, daily reports, costs).
 * The same panels appear as tabs on each project; this lets you reach them directly,
 * with a project picker. The choice is remembered, and `?project=<id>` links work.
 */
export function ProjectScopedPage({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: (projectId: string) => ReactNode;
}) {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const projectsQuery = useProjects();
  const projects = projectsQuery.data;
  const [projectId, setProjectId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  // Pick the project once the list arrives: from the link, then the last one used, then the first.
  useEffect(() => {
    if (!projects || projects.length === 0) return;
    const ids = new Set(projects.map((p) => p.id));
    const fromLink = new URLSearchParams(window.location.search).get("project");
    const remembered = readRemembered();
    setProjectId((current) =>
      [current, fromLink, remembered].find((id): id is string => !!id && ids.has(id)) ?? projects[0].id
    );
  }, [projects]);

  function choose(id: string) {
    setProjectId(id);
    try {
      window.localStorage.setItem(REMEMBERED_PROJECT, id);
    } catch {
      // storage blocked: the choice just won't be remembered
    }
    window.history.replaceState(null, "", `?project=${id}`);
  }

  if (authLoading || !user) return null;

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-ink">{title}</h1>
            <p className="text-muted">{description}</p>
          </div>
          {projects && projects.length > 0 && projectId && (
            <div className="flex items-center gap-2">
              <label htmlFor="scope-project" className="text-sm text-muted">
                Project
              </label>
              <select
                id="scope-project"
                className="h-9 rounded-md border border-border bg-surface px-2 text-sm"
                value={projectId}
                onChange={(e) => choose(e.target.value)}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.code})
                  </option>
                ))}
              </select>
              <Link href={`/projects/${projectId}`} className="text-sm text-primary hover:underline">
                Open project
              </Link>
            </div>
          )}
        </div>

        <QueryView
          query={projectsQuery}
          isEmpty={(list) => list.length === 0}
          empty={<EmptyState title="No projects yet" hint="Create a project first; this page works per project." />}
        >
          {/* Keyed so each panel starts fresh (forms, drafts) when the project changes. */}
          {() => (projectId ? <div key={projectId}>{children(projectId)}</div> : null)}
        </QueryView>
      </div>
    </AppShell>
  );
}
