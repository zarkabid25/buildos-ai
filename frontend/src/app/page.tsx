import Link from "next/link";
import type { Metadata } from "next";
import { ArrowRight, Boxes, Brain, Building2, CheckCircle2, LayoutDashboard, Network, ShieldCheck, Truck, Users2 } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";

export const metadata: Metadata = {
  title: "BuildOS AI — Construction ERP & Supplier Marketplace",
  description: "Know what happened. Know what's happening. Know what's next. The AI-native ERP and supplier marketplace built for construction companies.",
  openGraph: {
    title: "BuildOS AI — Construction ERP & Supplier Marketplace",
    description: "The AI-native ERP and supplier marketplace built for construction companies.",
    type: "website",
  },
};

const FAQ = [
  { q: "Is BuildOS AI only for large construction companies?", a: "No. BuildOS AI is built for construction companies of any size running projects, procurement and inventory -- plans scale from a single-project team to a multi-project operation." },
  { q: "Can suppliers join without a BuildOS AI subscription?", a: "Yes. Suppliers apply through our supplier network application, and once approved and verified by our team, get their own free Supplier Portal to manage their catalog, quote on RFQs, and track orders and commissions." },
  { q: "How does billing work?", a: "Construction companies choose a subscription plan with a free trial. Suppliers never pay a subscription -- they pay a commission only on marketplace-sourced purchase orders, under their own agreed terms." },
  { q: "Is my company's data visible to suppliers or other companies?", a: "No. Every company's projects, costs and inventory are strictly isolated. Suppliers only ever see the RFQs they're invited to and the orders attributed to them." },
];

export default function HomePage() {
  return (
    <div className="bg-slate-950">
      <MarketingNav />

      {/* 1. Hero */}
      <section className="relative overflow-hidden px-4 pb-24 pt-20 sm:px-6 sm:pt-28 lg:px-8">
        <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[500px] bg-gradient-to-b from-blue-900/30 to-transparent" />
        <div className="mx-auto max-w-4xl text-center">
          <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-blue-400">AI-Native Construction ERP</p>
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
            Know what happened.<br className="hidden sm:block" /> Know what&apos;s happening.<br className="hidden sm:block" /> Know what&apos;s next.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
            BuildOS AI brings projects, procurement, inventory and a verified supplier marketplace into one system -- with AI that actually understands your construction data.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link href="/register" className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3.5 text-base font-semibold text-white transition-colors hover:bg-blue-500">
              Start free trial <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/request-demo" className="rounded-lg border border-white/20 px-6 py-3.5 text-base font-semibold text-white transition-colors hover:bg-white/5">
              Request a demo
            </Link>
          </div>
        </div>
      </section>

      {/* 2. Value proposition */}
      <section className="border-y border-white/10 bg-slate-900 px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl text-center">
          <h2 className="text-3xl font-semibold text-white">One system for the whole construction lifecycle</h2>
          <p className="mx-auto mt-4 max-w-2xl text-slate-400">
            Projects, budgets, procurement, inventory, RFQs, purchase orders and goods receipts -- in one ERP, instead of spreadsheets stitched together after the fact.
          </p>
        </div>
      </section>

      {/* 3. Construction ERP features */}
      <section id="erp" className="bg-slate-950 px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-center text-3xl font-semibold text-white">Construction ERP, built for the job site</h2>
          <div className="mt-12 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { icon: Building2, title: "Projects & BOQ", desc: "Track budgets, bill of quantities, tasks, schedules and daily reports per project." },
              { icon: Boxes, title: "Inventory & Procurement", desc: "Materials, warehouses, stock transactions, RFQs, quotations and purchase orders." },
              { icon: LayoutDashboard, title: "Cost Control", desc: "Budgets, expenses, project costs and payments -- real numbers, not estimates." },
              { icon: Users2, title: "Workforce & Equipment", desc: "Attendance, employee assignments, and equipment maintenance tracking." },
              { icon: ShieldCheck, title: "Role-based Access", desc: "Super admin, company admin, project manager, site engineer, storekeeper, accountant and viewer roles." },
              { icon: Brain, title: "AI Command Center", desc: "An AI assistant that proposes -- never silently executes -- financial or inventory actions." },
            ].map((f) => (
              <div key={f.title} className="rounded-2xl border border-white/10 bg-slate-900/50 p-6">
                <f.icon className="h-8 w-8 text-blue-400" />
                <h3 className="mt-4 text-lg font-semibold text-white">{f.title}</h3>
                <p className="mt-2 text-sm text-slate-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. Supplier marketplace benefits */}
      <section className="border-y border-white/10 bg-slate-900 px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-center text-3xl font-semibold text-white">A verified supplier marketplace, built in</h2>
          <div className="mt-12 grid grid-cols-1 gap-8 lg:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-slate-950 p-8">
              <Network className="h-8 w-8 text-blue-400" />
              <h3 className="mt-4 text-xl font-semibold text-white">For construction companies</h3>
              <ul className="mt-4 space-y-3 text-sm text-slate-400">
                <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Discover and connect with verified suppliers by category and coverage area</li>
                <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Invite marketplace suppliers to your existing RFQs -- no second procurement system</li>
                <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Award, approve and receive goods through the same ERP flow you already use</li>
              </ul>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950 p-8">
              <Truck className="h-8 w-8 text-blue-400" />
              <h3 className="mt-4 text-xl font-semibold text-white">For suppliers</h3>
              <ul className="mt-4 space-y-3 text-sm text-slate-400">
                <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Your own free Supplier Portal to manage your catalog and team</li>
                <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Respond to RFQs and submit quotations directly</li>
                <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Track linked orders and your real commission statement -- no subscription, commission only on orders you actually win</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 5 & 6. AI capabilities + how it works */}
      <section className="bg-slate-950 px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-3xl font-semibold text-white">How BuildOS AI works</h2>
          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-4">
            {[
              { step: "1", title: "Set up your company", desc: "Register, pick a plan, and your trial starts immediately." },
              { step: "2", title: "Run your projects", desc: "Projects, procurement and inventory, in one ERP." },
              { step: "3", title: "Connect suppliers", desc: "Invite verified marketplace suppliers to quote on your RFQs." },
              { step: "4", title: "Let AI assist", desc: "AI drafts proposals for review -- a human always approves before anything is committed." },
            ].map((s) => (
              <div key={s.step} className="rounded-2xl border border-white/10 bg-slate-900/50 p-6">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white">{s.step}</span>
                <h3 className="mt-4 text-base font-semibold text-white">{s.title}</h3>
                <p className="mt-2 text-sm text-slate-400">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 9. Pricing overview */}
      <section className="border-y border-white/10 bg-slate-900 px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="text-3xl font-semibold text-white">Simple, plan-based pricing</h2>
          <p className="mt-4 text-slate-400">Real plans, priced and managed by our team -- never hardcoded. See exact current pricing on our pricing page.</p>
          <Link href="/pricing" className="mt-8 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-500">
            View pricing <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* 10. FAQ */}
      <section className="bg-slate-950 px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-center text-3xl font-semibold text-white">Frequently asked questions</h2>
          <div className="mt-10 divide-y divide-white/10">
            {FAQ.map((f) => (
              <div key={f.q} className="py-6">
                <h3 className="text-base font-semibold text-white">{f.q}</h3>
                <p className="mt-2 text-sm text-slate-400">{f.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 11. Final CTA */}
      <section className="bg-blue-600 px-4 py-20 text-center sm:px-6 lg:px-8">
        <h2 className="text-3xl font-semibold text-white">Ready to see what BuildOS AI can do for your projects?</h2>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Link href="/register" className="rounded-lg bg-white px-6 py-3.5 text-base font-semibold text-blue-700 hover:bg-blue-50">
            Start free trial
          </Link>
          <Link href="/request-demo" className="rounded-lg border border-white/40 px-6 py-3.5 text-base font-semibold text-white hover:bg-white/10">
            Request a demo
          </Link>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
