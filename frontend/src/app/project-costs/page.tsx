"use client";

import { CostsPanel } from "@/components/costs-panel";
import { ProjectScopedPage } from "@/components/project-scoped-page";

export default function ProjectCostsPage() {
  return (
    <ProjectScopedPage
      title="Project Costs"
      description="Budget, committed and actual spend, and the forecast at completion for one project."
    >
      {(projectId) => <CostsPanel projectId={projectId} />}
    </ProjectScopedPage>
  );
}
