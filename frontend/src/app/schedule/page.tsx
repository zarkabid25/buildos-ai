"use client";

import { ProjectScopedPage } from "@/components/project-scoped-page";
import { SchedulePanel } from "@/components/schedule-panel";

export default function SchedulePage() {
  return (
    <ProjectScopedPage title="Schedule" description="Task timeline, dependencies and schedule variance per project.">
      {(projectId) => <SchedulePanel projectId={projectId} />}
    </ProjectScopedPage>
  );
}
