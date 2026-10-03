"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { useFeedback } from "@/components/feedback";
import { DocumentSearch } from "@/components/document-search";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  DOCUMENT_CATEGORIES,
  fetchDocumentBlob,
  useDeleteDocument,
  useDocuments,
  useUploadDocument,
  type DocumentCategory,
  type DocumentItem,
} from "@/lib/use-documents";
import { useProjects } from "@/lib/use-projects";

const PREVIEWABLE = new Set([
  "application/pdf",
  "text/plain",
  "text/csv",
  "image/jpeg",
  "image/png",
  "image/webp",
]);

function formatSize(bytes: number) {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${bytes} B`;
}

const TEXT_STATUS: Record<NonNullable<DocumentItem["text_status"]>, { label: string; className: string; hint: string }> = {
  indexed: { label: "Yes", className: "text-success", hint: "Its text can be searched" },
  no_text: { label: "No text", className: "text-warning", hint: "No text layer, e.g. a scanned page; it can't be searched" },
  unsupported: { label: "—", className: "text-muted", hint: "Images and old .doc/.xls files aren't searched" },
  failed: { label: "Couldn't read", className: "text-danger", hint: "The file couldn't be read for search" },
};

function TextStatus({ status, pages }: { status: DocumentItem["text_status"]; pages: number | null }) {
  if (!status) return <span className="text-muted" title="Not indexed yet">Not yet</span>;
  const s = TEXT_STATUS[status];
  return (
    <span className={s.className} title={s.hint}>
      {s.label}
      {status === "indexed" && pages ? ` · ${pages} page${pages === 1 ? "" : "s"}` : ""}
    </span>
  );
}

export default function DocumentsPage() {
  const { user, accessToken, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const { confirm } = useFeedback();
  const [filter, setFilter] = useState<DocumentCategory | "">("");
  const { data: documents, isLoading, isError, error: loadError, refetch } = useDocuments(filter);
  const { data: projects } = useProjects();
  const upload = useUploadDocument();
  const remove = useDeleteDocument();

  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState({
    title: "",
    category: "other" as DocumentCategory,
    project_id: "",
    description: "",
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  async function handleUpload() {
    setError(null);
    if (!file) return setError("Choose a file first");
    if (!form.title.trim()) return setError("Give the document a title");
    try {
      await upload.mutateAsync({
        file,
        title: form.title.trim(),
        category: form.category,
        project_id: form.project_id || undefined,
        description: form.description || undefined,
      });
      setFile(null);
      setForm({ title: "", category: "other", project_id: "", description: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    }
  }

  async function open(doc: Pick<DocumentItem, "id" | "original_filename">, mode: "preview" | "download", page?: number | null) {
    if (!accessToken) return;
    setError(null);
    try {
      const blob = await fetchDocumentBlob(doc.id, accessToken, mode === "preview");
      const url = URL.createObjectURL(blob);
      if (mode === "preview") {
        // Browsers' PDF viewers open at the given page with #page=N.
        window.open(page ? `${url}#page=${page}` : url, "_blank", "noopener");
      } else {
        const a = window.document.createElement("a");
        a.href = url;
        a.download = doc.original_filename;
        a.click();
      }
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not open document");
    }
  }

  async function handleDelete(doc: DocumentItem) {
    const ok = await confirm({
      title: `Delete "${doc.title}"?`,
      body: "The file is removed from storage. This can't be undone.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    setError(null);
    try {
      await remove.mutateAsync(doc.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete document");
    }
  }

  const projectName = (id: string | null) => projects?.find((p) => p.id === id)?.name ?? "—";

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Documents</h1>
          <p className="text-muted">Contracts, drawings, invoices and other project files.</p>
        </div>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink">Upload a document</h2>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Input
              placeholder="Title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <select
              className="h-9 rounded-md border border-border bg-surface px-2 text-sm"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value as DocumentCategory })}
            >
              {DOCUMENT_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <select
              className="h-9 rounded-md border border-border bg-surface px-2 text-sm"
              value={form.project_id}
              onChange={(e) => setForm({ ...form, project_id: e.target.value })}
            >
              <option value="">No project (company-wide)</option>
              {projects?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <Input
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
            <input
              type="file"
              className="text-sm sm:col-span-2"
              accept=".pdf,.txt,.csv,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.webp"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          {error && <p className="mt-2 text-sm text-danger">{error}</p>}
          <Button className="mt-3" onClick={handleUpload} disabled={upload.isPending}>
            {upload.isPending ? "Uploading..." : "Upload"}
          </Button>
        </Card>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted">Category:</span>
          <select
            className="h-8 rounded-md border border-border bg-surface px-2 text-sm"
            value={filter}
            onChange={(e) => setFilter(e.target.value as DocumentCategory | "")}
          >
            <option value="">All</option>
            {DOCUMENT_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <DocumentSearch
          onOpen={(hit) => {
            // The list may be filtered to another category; the server decides inline vs download anyway.
            const doc = documents?.find((d) => d.id === hit.document_id);
            const mode = !doc || PREVIEWABLE.has(doc.content_type) ? "preview" : "download";
            open(doc ?? { id: hit.document_id, original_filename: hit.title }, mode, hit.page);
          }}
        />

        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-4 py-3 font-medium">Project</th>
                <th className="px-4 py-3 font-medium">Size</th>
                <th className="px-4 py-3 font-medium">Searchable</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading &&
                [0, 1, 2].map((i) => (
                  <tr key={i}>
                    <td colSpan={6} className="px-4 py-3">
                      <Skeleton className="h-5 w-full" />
                    </td>
                  </tr>
                ))}
              {isError && (
                <tr>
                  <td colSpan={6} className="p-3">
                    <ErrorState error={loadError} onRetry={() => refetch()} />
                  </td>
                </tr>
              )}
              {!isLoading && !isError && (!documents || documents.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-muted">
                    No documents yet.
                  </td>
                </tr>
              )}
              {documents?.map((doc) => (
                <tr key={doc.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3">
                    <div className="font-medium text-ink">{doc.title}</div>
                    <div className="text-xs text-muted">{doc.original_filename}</div>
                  </td>
                  <td className="px-4 py-3 text-muted">{doc.category}</td>
                  <td className="px-4 py-3 text-muted">{projectName(doc.project_id)}</td>
                  <td className="px-4 py-3 text-muted">{formatSize(doc.size_bytes)}</td>
                  <td className="px-4 py-3 text-xs">
                    <TextStatus status={doc.text_status} pages={doc.page_count} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-xs">
                    {PREVIEWABLE.has(doc.content_type) && (
                      <button
                        className="mr-3 text-primary hover:underline"
                        onClick={() => open(doc, "preview")}
                      >
                        Preview
                      </button>
                    )}
                    <button
                      className="mr-3 text-primary hover:underline"
                      onClick={() => open(doc, "download")}
                    >
                      Download
                    </button>
                    <button className="text-muted hover:text-danger" onClick={() => handleDelete(doc)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </AppShell>
  );
}
