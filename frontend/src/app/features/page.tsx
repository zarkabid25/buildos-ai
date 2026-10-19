import Link from "next/link";
import type { Metadata } from "next";
import { ArrowRight, Boxes, Brain, Building2, FileText, LayoutDashboard, ShieldCheck, Truck, Users2, Wallet } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";

export const metadata: Metadata = {
  title: "Features — BuildOS AI",
  description: "Every module in BuildOS AI: projects, procurement, inventory, cost control, workforce, the supplier marketplace, and AI assistance.",
};

const MODULES = [
  { icon: Building2, title: "Projects & BOQ", desc: "Projects, bill of quantities, tasks, dependencies, schedules and daily site reports." },
  { icon: Boxes, title: "Inventory", desc: "Materials, warehouses, stock transactions and real-time stock levels." },
  { icon: FileText, title: "RFQs & Procurement", desc: "Material requests, RFQs, supplier quotations, comparison, and purchase orders." },
  { icon: Truck, title: "Supplier Marketplace", desc: "A verified, cross-tenant supplier registry your company can connect to directly." },
  { icon: Wallet, title: "Cost Control", desc: "Budgets, expenses, project costs, client receipts and supplier payments." },
  { icon: Users2, title: "Workforce & Equipment", desc: "Employee project assignments, attendance, and equipment maintenance." },
  { icon: ShieldCheck, title: "Roles & Audit", desc: "Seven tenant roles, a full audit log, and strict company-by-company data isolation." },
  { icon: Brain, title: "AI Assistant", desc: "An AI command center and AI-drafted proposals -- always reviewed by a human before anything financial or inventory-related is committed." },
];

export default function FeaturesPage() {
  return (
    <div className="bg-slate-950">
      <MarketingNav />
      <section className="px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="text-4xl font-bold text-white sm:text-5xl">Everything your construction business runs on</h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-400">One system, not six disconnected tools.</p>
        </div>
        <div className="mx-auto mt-16 grid max-w-6xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {MODULES.map((m) => (
            <div key={m.title} className="rounded-2xl border border-white/10 bg-slate-900/50 p-6">
              <m.icon className="h-8 w-8 text-blue-400" />
              <h3 className="mt-4 text-base font-semibold text-white">{m.title}</h3>
              <p className="mt-2 text-sm text-slate-400">{m.desc}</p>
            </div>
          ))}
        </div>
        <div className="mt-16 flex justify-center">
          <Link href="/register" className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3.5 text-base font-semibold text-white hover:bg-blue-500">
            Start free trial <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
      <section className="border-t border-white/10 bg-slate-900 px-4 py-16 text-center sm:px-6 lg:px-8">
        <LayoutDashboard className="mx-auto h-10 w-10 text-blue-400" />
        <h2 className="mt-4 text-2xl font-semibold text-white">One dashboard for every project</h2>
        <p className="mx-auto mt-3 max-w-xl text-slate-400">Everything above lives behind a single sign-in, scoped to your company, with role-based access for your whole team.</p>
      </section>
      <MarketingFooter />
    </div>
  );
}
