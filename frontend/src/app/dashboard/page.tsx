"use client";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) return null;

  const firstName = user.full_name.split(" ")[0];

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Good morning, {firstName}</h1>
          <p className="text-muted">Here&apos;s what&apos;s happening across your construction business.</p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "Projects", value: "0" },
            { label: "Project Value", value: "PKR 0" },
            { label: "Avg Progress", value: "0%" },
            { label: "At Risk", value: "0" },
          ].map((stat) => (
            <div key={stat.label} className="rounded-card border border-border bg-surface p-4">
              <div className="text-2xl font-semibold text-ink">{stat.value}</div>
              <div className="text-sm text-muted">{stat.label}</div>
            </div>
          ))}
        </div>

        <div className="rounded-card border border-border bg-surface p-5">
          <h2 className="mb-2 text-sm font-semibold text-ink">AI Executive Summary</h2>
          <p className="text-sm text-muted">
            No data yet. Create your first project to get AI-powered insights here.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
