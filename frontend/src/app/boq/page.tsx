"use client";

import { BoqPanel } from "@/components/boq-panel";
import { ProjectScopedPage } from "@/components/project-scoped-page";

export default function BoqPage() {
  return (
    <ProjectScopedPage title="BOQ" description="Bill of quantities per project, and how actual material use compares.">
      {(projectId) => <BoqPanel projectId={projectId} />}
    </ProjectScopedPage>
  );
}
