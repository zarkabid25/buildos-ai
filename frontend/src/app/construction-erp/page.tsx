import Link from "next/link";
import type { Metadata } from "next";
import { ArrowRight, CheckCircle2 } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";

export const metadata: Metadata = {
  title: "Construction ERP — BuildOS AI",
  description: "Projects, budgets, procurement and inventory in one construction ERP -- built for how construction companies actually work.",
};

const BENEFITS = [
  "Real budgets and project costs, not spreadsheet estimates that drift from reality",
  "One procurement flow from material request through RFQ, quotation, purchase order and goods receipt",
  "Inventory that actually reflects what's in your warehouses, updated by real stock transactions",
  "Daily site reports, task dependencies and schedules your project managers actually use",
  "Workforce attendance and equipment maintenance tracked alongside the project they belong to",
  "A real audit log and company-level isolation, so your data is yours alone",
];

export default function ConstructionErpPage() {
  return (
    <div className="bg-slate-950">
      <MarketingNav />
      <section className="px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <h1 className="text-4xl font-bold text-white sm:text-5xl">A construction ERP built around the real project lifecycle</h1>
            <p className="mt-5 text-lg text-slate-400">From the first budget line to the last goods receipt, BuildOS AI tracks what actually happened on your projects -- not what a spreadsheet says should have happened.</p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link href="/register" className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3.5 text-base font-semibold text-white hover:bg-blue-500">
                Start free trial <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/request-demo" className="rounded-lg border border-white/20 px-6 py-3.5 text-base font-semibold text-white hover:bg-white/5">
                Request a demo
              </Link>
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-8">
            <ul className="space-y-4">
              {BENEFITS.map((b) => (
                <li key={b} className="flex gap-3 text-sm text-slate-300">
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />
                  {b}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
      <MarketingFooter />
    </div>
  );
}
