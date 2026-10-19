"use client";

import { useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useSubmitSupplierApplication, uploadSupplierApplicationDocument } from "@/lib/use-public";

export default function BecomeASupplierPage() {
  const submitApplication = useSubmitSupplierApplication();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState({
    business_name: "", contact_name: "", email: "", phone: "", business_registration_info: "", categories: "", delivery_locations: "", business_description: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const result = await submitApplication.mutateAsync({
        business_name: form.business_name, contact_name: form.contact_name, email: form.email,
        phone: form.phone || undefined, business_registration_info: form.business_registration_info || undefined,
        categories: form.categories.split(",").map((c) => c.trim()).filter(Boolean),
        delivery_locations: form.delivery_locations.split(",").map((c) => c.trim()).filter(Boolean),
        business_description: form.business_description || undefined,
      });
      const file = fileInputRef.current?.files?.[0];
      if (file) {
        await uploadSupplierApplicationDocument(result.id, file, file.name);
      }
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    }
  }

  return (
    <div className="bg-slate-950">
      <MarketingNav />
      <section className="px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-lg">
          <h1 className="text-3xl font-bold text-white sm:text-4xl">Become a supplier</h1>
          <p className="mt-3 text-slate-400">Apply to join the BuildOS AI supplier network. Every application is reviewed by our team -- nothing is approved or verified automatically.</p>

          {done ? (
            <div className="mt-10 flex flex-col items-center gap-3 rounded-2xl border border-white/10 bg-slate-900/50 p-10 text-center">
              <CheckCircle2 className="h-10 w-10 text-blue-400" />
              <p className="text-lg font-semibold text-white">Application submitted</p>
              <p className="text-sm text-slate-400">Our team will review your application and follow up by email. This can take a few business days.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-10 space-y-4 rounded-2xl border border-white/10 bg-slate-900/50 p-8">
              <div>
                <Label htmlFor="business_name" className="text-slate-300">Business name</Label>
                <Input id="business_name" required value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="contact_name" className="text-slate-300">Contact person</Label>
                <Input id="contact_name" required value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="email" className="text-slate-300">Email</Label>
                  <Input id="email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div>
                  <Label htmlFor="phone" className="text-slate-300">Phone</Label>
                  <Input id="phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </div>
              </div>
              <div>
                <Label htmlFor="registration" className="text-slate-300">Business registration info (optional)</Label>
                <Input id="registration" value={form.business_registration_info} onChange={(e) => setForm({ ...form, business_registration_info: e.target.value })} placeholder="Registration number, license, etc." />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="categories" className="text-slate-300">Product categories</Label>
                  <Input id="categories" placeholder="cement, steel, ..." value={form.categories} onChange={(e) => setForm({ ...form, categories: e.target.value })} />
                </div>
                <div>
                  <Label htmlFor="locations" className="text-slate-300">Delivery locations</Label>
                  <Input id="locations" placeholder="Punjab, Sindh, ..." value={form.delivery_locations} onChange={(e) => setForm({ ...form, delivery_locations: e.target.value })} />
                </div>
              </div>
              <div>
                <Label htmlFor="description" className="text-slate-300">Business description</Label>
                <textarea
                  id="description"
                  value={form.business_description}
                  onChange={(e) => setForm({ ...form, business_description: e.target.value })}
                  rows={3}
                  className="w-full rounded-md border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <Label htmlFor="document" className="text-slate-300">Supporting document (optional)</Label>
                <input ref={fileInputRef} id="document" type="file" className="block w-full text-sm text-slate-300" />
              </div>
              {error && <p className="text-sm text-red-400">{error}</p>}
              <Button type="submit" className="h-11 w-full text-base" disabled={submitApplication.isPending}>
                {submitApplication.isPending ? "Submitting..." : "Submit application"}
              </Button>
              <p className="text-xs text-slate-500">Submitting does not create a live marketplace listing -- your application is reviewed first.</p>
            </form>
          )}
        </div>
      </section>
      <MarketingFooter />
    </div>
  );
}
