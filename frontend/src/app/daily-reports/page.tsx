"use client";

import { DailyReportsPanel } from "@/components/daily-reports-panel";
import { ProjectScopedPage } from "@/components/project-scoped-page";

export default function DailyReportsPage() {
  return (
    <ProjectScopedPage title="Daily Reports" description="Site diaries: work done, weather, issues and photos.">
      {(projectId) => <DailyReportsPanel projectId={projectId} />}
    </ProjectScopedPage>
  );
}
