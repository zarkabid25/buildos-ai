"use client";

import { useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useRequestDemo } from "@/lib/use-public";

export default function RequestDemoPage() {
  const requestDemo = useRequestDemo();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", company_name: "", message: "" });
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await requestDemo.mutateAsync({ ...form, phone: form.phone || undefined, message: form.message || undefined });
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
          <h1 className="text-3xl font-bold text-white sm:text-4xl">Request a demo</h1>
          <p className="mt-3 text-slate-400">Tell us a bit about your company and we'll reach out to schedule a walkthrough.</p>

          {done ? (
            <div className="mt-10 flex flex-col items-center gap-3 rounded-2xl border border-white/10 bg-slate-900/50 p-10 text-center">
              <CheckCircle2 className="h-10 w-10 text-blue-400" />
              <p className="text-lg font-semibold text-white">Request received</p>
              <p className="text-sm text-slate-400">We'll be in touch at the email you provided. In the meantime, feel free to explore our <a href="/pricing" className="text-blue-400 hover:underline">pricing</a>.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-10 space-y-4 rounded-2xl border border-white/10 bg-slate-900/50 p-8">
              <div>
                <Label htmlFor="full_name" className="text-slate-300">Full name</Label>
                <Input id="full_name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="email" className="text-slate-300">Work email</Label>
                <Input id="email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="phone" className="text-slate-300">Phone (optional)</Label>
                <Input id="phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="company_name" className="text-slate-300">Company name</Label>
                <Input id="company_name" required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="message" className="text-slate-300">What are you hoping to solve? (optional)</Label>
                <textarea
                  id="message"
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                  rows={3}
                  className="w-full rounded-md border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white"
                />
              </div>
              {error && <p className="text-sm text-red-400">{error}</p>}
              <Button type="submit" className="h-11 w-full text-base" disabled={requestDemo.isPending}>
                {requestDemo.isPending ? "Submitting..." : "Request demo"}
              </Button>
              <p className="text-xs text-slate-500">By submitting, you agree we may contact you about BuildOS AI. We never share your information with suppliers or other companies.</p>
            </form>
          )}
        </div>
      </section>
      <MarketingFooter />
    </div>
  );
}
