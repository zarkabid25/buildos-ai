"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState } from "@/components/ui/states";
import type { MarketplaceSupplierStatus } from "@/lib/marketplace-types";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import {
  fetchMarketplaceDocumentBlob,
  useAddMarketplaceContact,
  useAddMarketplaceProduct,
  useLinkMarketplaceCompany,
  useMarketplaceCompanyLinks,
  useMarketplaceSupplier,
  useMarketplaceSupplierActivity,
  useSetVerificationStatus,
  useUploadMarketplaceDocument,
} from "@/lib/use-marketplace";

const STATUS_ACTIONS: Record<MarketplaceSupplierStatus, { to: MarketplaceSupplierStatus; label: string }[]> = {
  pending: [
    { to: "verified", label: "Verify" },
    { to: "rejected", label: "Reject" },
  ],
  verified: [
    { to: "suspended", label: "Suspend" },
    { to: "rejected", label: "Reject" },
  ],
  suspended: [{ to: "verified", label: "Reactivate" }],
  rejected: [{ to: "pending", label: "Reconsider" }],
};

const contactSchema = z.object({
  name: z.string().trim().min(1, "Name is required"),
  role: z.string().trim().optional(),
  email: z.string().trim().email("Enter a valid email").optional().or(z.literal("")),
});
type ContactInput = z.infer<typeof contactSchema>;

const productSchema = z.object({
  name: z.string().trim().min(1, "Required"),
  unit: z.string().trim().min(1, "Required"),
  price: z.string().trim().min(1, "Required"),
  minimum_order_quantity: z.string().trim().optional(),
  lead_time_days: z.string().trim().optional(),
});
type ProductInput = z.infer<typeof productSchema>;

export default function MarketplaceSupplierDetailPage() {
  const { admin, isLoading, accessToken } = usePlatformAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast, confirm } = useFeedback();
  const isReadOnly = admin?.role === "support";
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [docTitle, setDocTitle] = useState("");
  const [companyIdInput, setCompanyIdInput] = useState("");

  const { data: supplier, isLoading: supplierLoading, isError, error, refetch } = useMarketplaceSupplier(params.id);
  const { data: activity } = useMarketplaceSupplierActivity(params.id);
  const { data: links } = useMarketplaceCompanyLinks(params.id);
  const setVerification = useSetVerificationStatus();
  const addContact = useAddMarketplaceContact();
  const addProduct = useAddMarketplaceProduct();
  const uploadDocument = useUploadMarketplaceDocument();
  const linkCompany = useLinkMarketplaceCompany();

  const contactForm = useForm<ContactInput>({ resolver: zodResolver(contactSchema) });
  const productForm = useForm<ProductInput>({ resolver: zodResolver(productSchema) });

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function handleVerification(to: MarketplaceSupplierStatus, label: string) {
    if (!supplier) return;
    const ok = await confirm({ title: `${label} ${supplier.name}?`, confirmLabel: label });
    if (!ok) return;
    try {
      await setVerification.mutateAsync({ id: supplier.id, status: to });
      toast(`${supplier.name} ${label.toLowerCase()}ed.`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function onAddContact(values: ContactInput) {
    if (!supplier) return;
    try {
      await addContact.mutateAsync({ supplierId: supplier.id, ...values, email: values.email || undefined });
      contactForm.reset();
      toast("Contact added.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function onAddProduct(values: ProductInput) {
    if (!supplier) return;
    try {
      await addProduct.mutateAsync({
        supplierId: supplier.id,
        name: values.name,
        unit: values.unit,
        price: values.price,
        minimum_order_quantity: values.minimum_order_quantity || undefined,
        lead_time_days: values.lead_time_days ? Number(values.lead_time_days) : undefined,
      });
      productForm.reset();
      toast("Product added.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleUpload() {
    const file = fileInputRef.current?.files?.[0];
    if (!file || !supplier) return;
    try {
      await uploadDocument.mutateAsync({ supplierId: supplier.id, file, title: docTitle || file.name });
      setDocTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      toast("Document uploaded.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Upload failed.", "error");
    }
  }

  async function handleDownload(documentId: string, filename: string) {
    if (!supplier || !accessToken) return;
    try {
      const blob = await fetchMarketplaceDocumentBlob(supplier.id, documentId, accessToken);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Couldn't download.", "error");
    }
  }

  async function handleLinkCompany() {
    if (!supplier || !companyIdInput) return;
    try {
      await linkCompany.mutateAsync({ supplierId: supplier.id, company_id: companyIdInput });
      setCompanyIdInput("");
      toast("Company linked.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb={supplier ? supplier.name : "Marketplace"}>
      <div className="max-w-3xl space-y-5">
        {supplierLoading && <div className="h-32 animate-pulse rounded-[14px] bg-[var(--bo-nav-active)]" />}
        {isError && <ErrorState error={error} onRetry={() => refetch()} />}
        {supplier && (
          <>
            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h1 className="text-2xl font-semibold tracking-[-0.025em] text-[var(--bo-text)]">{supplier.name}</h1>
                  <p className="mt-1 text-sm text-[var(--bo-text-muted)]">
                    {supplier.categories.join(", ") || "No categories"} &middot; {supplier.coverage_areas.join(", ") || "No coverage areas"}
                  </p>
                  <p className="mt-1 text-sm text-[var(--bo-text-muted)]">
                    Status: <span className="font-medium text-[var(--bo-text)]">{supplier.verification_status}</span>
                    {" "}&middot; onboarded by {supplier.onboarded_by_name ?? "—"}
                  </p>
                </div>
                {!isReadOnly && (
                  <div className="flex gap-2">
                    {STATUS_ACTIONS[supplier.verification_status].map((action) => (
                      <Button key={action.to} variant="secondary" onClick={() => handleVerification(action.to, action.label)}>
                        {action.label}
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Contacts</h2>
              {supplier.contacts.length === 0 && <p className="mt-2 text-sm text-[var(--bo-text-muted)]">No contacts yet.</p>}
              <ul className="mt-2 divide-y divide-[var(--bo-divider)]">
                {supplier.contacts.map((c) => (
                  <li key={c.id} className="py-2 text-sm">
                    <span className="font-medium text-[var(--bo-text)]">{c.name}</span>
                    {c.role && <span className="text-[var(--bo-text-muted)]"> &middot; {c.role}</span>}
                    {c.email && <span className="text-[var(--bo-text-muted)]"> &middot; {c.email}</span>}
                  </li>
                ))}
              </ul>
              {!isReadOnly && (
                <form onSubmit={contactForm.handleSubmit(onAddContact)} className="mt-4 grid gap-3 sm:grid-cols-4">
                  <Input placeholder="Name" {...contactForm.register("name")} />
                  <Input placeholder="Role" {...contactForm.register("role")} />
                  <Input placeholder="Email" {...contactForm.register("email")} />
                  <Button type="submit" variant="secondary" disabled={contactForm.formState.isSubmitting}>
                    Add contact
                  </Button>
                </form>
              )}
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Verification Documents</h2>
              {supplier.documents.length === 0 && <p className="mt-2 text-sm text-[var(--bo-text-muted)]">No documents yet.</p>}
              <ul className="mt-2 divide-y divide-[var(--bo-divider)]">
                {supplier.documents.map((d) => (
                  <li key={d.id} className="flex items-center justify-between py-2 text-sm">
                    <span>{d.title}</span>
                    <button onClick={() => handleDownload(d.id, d.original_filename)} className="text-xs font-medium text-[var(--bo-primary)]">
                      Download
                    </button>
                  </li>
                ))}
              </ul>
              {!isReadOnly && (
                <div className="mt-4 flex flex-wrap items-end gap-3">
                  <div>
                    <Label htmlFor="doc-title">Title</Label>
                    <Input id="doc-title" value={docTitle} onChange={(e) => setDocTitle(e.target.value)} />
                  </div>
                  <input ref={fileInputRef} type="file" className="text-sm" />
                  <Button variant="secondary" onClick={handleUpload} disabled={uploadDocument.isPending}>
                    Upload
                  </Button>
                </div>
              )}
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Product Catalog</h2>
              {supplier.products.length === 0 && <p className="mt-2 text-sm text-[var(--bo-text-muted)]">No products yet.</p>}
              <ul className="mt-2 divide-y divide-[var(--bo-divider)]">
                {supplier.products.map((p) => (
                  <li key={p.id} className="py-2 text-sm">
                    <span className="font-medium text-[var(--bo-text)]">{p.name}</span>
                    <span className="text-[var(--bo-text-muted)]">
                      {" "}&middot; {p.price}/{p.unit} &middot; min {p.minimum_order_quantity} {p.unit}
                      {p.lead_time_days != null && ` · ${p.lead_time_days}d lead time`}
                    </span>
                  </li>
                ))}
              </ul>
              {!isReadOnly && (
                <form onSubmit={productForm.handleSubmit(onAddProduct)} className="mt-4 grid gap-3 sm:grid-cols-5">
                  <Input placeholder="Name" {...productForm.register("name")} />
                  <Input placeholder="Unit (bag, ton...)" {...productForm.register("unit")} />
                  <Input placeholder="Price" {...productForm.register("price")} />
                  <Input placeholder="Min qty" {...productForm.register("minimum_order_quantity")} />
                  <Button type="submit" variant="secondary" disabled={productForm.formState.isSubmitting}>
                    Add
                  </Button>
                </form>
              )}
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Connected Companies</h2>
              <p className="mt-0.5 text-xs text-[var(--bo-text-muted)]">
                Groundwork for future integration -- nothing in procurement reads this yet.
              </p>
              {(!links || links.length === 0) && <p className="mt-2 text-sm text-[var(--bo-text-muted)]">No companies linked.</p>}
              <ul className="mt-2 divide-y divide-[var(--bo-divider)]">
                {links?.map((l) => (
                  <li key={l.id} className="py-2 text-sm">
                    {l.company_name}
                  </li>
                ))}
              </ul>
              {!isReadOnly && (
                <div className="mt-4 flex items-end gap-2">
                  <div>
                    <Label htmlFor="company-id">Company ID</Label>
                    <Input id="company-id" value={companyIdInput} onChange={(e) => setCompanyIdInput(e.target.value)} />
                  </div>
                  <Button variant="secondary" onClick={handleLinkCompany} disabled={linkCompany.isPending || !companyIdInput}>
                    Link
                  </Button>
                </div>
              )}
            </div>

            <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
              <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Activity History</h2>
              {(!activity || activity.length === 0) && <p className="mt-2 text-sm text-[var(--bo-text-muted)]">Nothing yet.</p>}
              <ul className="mt-2 divide-y divide-[var(--bo-divider)]">
                {activity?.map((a) => (
                  <li key={a.id} className="py-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--bo-text)]">{a.summary}</span>
                      <span className="text-xs text-[var(--bo-text-muted)]">{new Date(a.created_at).toLocaleString()}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </PlatformShell>
  );
}
