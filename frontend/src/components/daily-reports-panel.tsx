"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  fetchPhotoBlobUrl,
  useCreateDailyReport,
  useDailyReports,
  useUploadReportPhoto,
  type DailyReport,
} from "@/lib/use-daily-reports";

function ReportPhoto({ reportId, photoId, name }: { reportId: string; photoId: string; name: string }) {
  const { accessToken } = useAuth();
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    let url: string | null = null;
    let cancelled = false;
    fetchPhotoBlobUrl(reportId, photoId, accessToken)
      .then((u) => {
        if (cancelled) URL.revokeObjectURL(u);
        else {
          url = u;
          setSrc(u);
        }
      })
      .catch(() => setSrc(null));
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [reportId, photoId, accessToken]);

  if (!src) return <div className="h-24 w-24 rounded-md bg-gray-100" />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={name} className="h-24 w-24 rounded-md object-cover" />;
}

function ReportCard({ report, projectId }: { report: DailyReport; projectId: string }) {
  const upload = useUploadReportPhoto(projectId);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    try {
      await upload.mutateAsync({ reportId: report.id, file });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    }
  }

  const fields: [string, string | null][] = [
    ["Work completed", report.work_completed],
    ["Materials consumed", report.materials_consumed],
    ["Equipment", report.equipment_used],
    ["Problems", report.problems],
    ["Notes", report.notes],
  ];

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-semibold text-ink">{report.report_date}</div>
        <div className="text-xs text-muted">
          {report.weather ?? "Weather not recorded"} · {report.workers_count} workers
        </div>
      </div>
      <dl className="space-y-1 text-sm">
        {fields.map(
          ([label, value]) =>
            value && (
              <div key={label}>
                <dt className="inline text-xs uppercase text-muted">{label}: </dt>
                <dd className="inline text-ink">{value}</dd>
              </div>
            )
        )}
      </dl>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {report.photos.map((p) => (
          <ReportPhoto key={p.id} reportId={report.id} photoId={p.id} name={p.original_filename} />
        ))}
        <label className="cursor-pointer rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted hover:bg-gray-50">
          {upload.isPending ? "Uploading..." : "+ Add photo"}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              handleFile(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </label>
      </div>
      {error && <p className="mt-2 text-xs text-danger">{error}</p>}
    </Card>
  );
}

export function DailyReportsPanel({ projectId }: { projectId: string }) {
  const { data: reports } = useDailyReports(projectId);
  const create = useCreateDailyReport(projectId);

  const [form, setForm] = useState({
    report_date: new Date().toISOString().slice(0, 10),
    weather: "",
    workers_count: "",
    work_completed: "",
    problems: "",
  });
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    setError(null);
    try {
      await create.mutateAsync({
        report_date: form.report_date,
        weather: form.weather || undefined,
        workers_count: form.workers_count ? Number(form.workers_count) : 0,
        work_completed: form.work_completed || undefined,
        problems: form.problems || undefined,
      });
      setForm({ ...form, weather: "", workers_count: "", work_completed: "", problems: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save report");
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-3 text-sm font-semibold text-ink">New daily report</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <Input type="date" value={form.report_date} onChange={(e) => setForm({ ...form, report_date: e.target.value })} />
          <Input placeholder="Weather" value={form.weather} onChange={(e) => setForm({ ...form, weather: e.target.value })} />
          <Input type="number" placeholder="Workers on site" value={form.workers_count} onChange={(e) => setForm({ ...form, workers_count: e.target.value })} />
          <Input className="sm:col-span-3" placeholder="Work completed today" value={form.work_completed} onChange={(e) => setForm({ ...form, work_completed: e.target.value })} />
          <Input className="sm:col-span-3" placeholder="Problems / delays" value={form.problems} onChange={(e) => setForm({ ...form, problems: e.target.value })} />
        </div>
        {error && <p className="mt-2 text-sm text-danger">{error}</p>}
        <Button className="mt-3" onClick={handleCreate} disabled={create.isPending}>
          Save report
        </Button>
        <p className="mt-2 text-xs text-muted">Photos can be added to each report after it&apos;s saved.</p>
      </Card>

      {(!reports || reports.length === 0) && (
        <Card className="text-center text-sm text-muted">No daily reports yet.</Card>
      )}
      {reports?.map((r) => (
        <ReportCard key={r.id} report={r} projectId={projectId} />
      ))}
    </div>
  );
}
