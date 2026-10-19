import Link from "next/link";
import type { Metadata } from "next";
import { ArrowRight, CheckCircle2, ShieldCheck, Truck } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";

export const metadata: Metadata = {
  title: "Supplier Network — BuildOS AI",
  description: "A verified construction supplier marketplace connected directly to the ERP -- for construction companies and suppliers alike.",
};

export default function SupplierNetworkPage() {
  return (
    <div className="bg-slate-950">
      <MarketingNav />
      <section className="px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <ShieldCheck className="mx-auto h-10 w-10 text-blue-400" />
          <h1 className="mt-4 text-4xl font-bold text-white sm:text-5xl">A verified supplier network, not an open marketplace</h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-400">Every supplier is reviewed and verified by our team before construction companies can connect with them -- never automatic.</p>
        </div>

        <div className="mx-auto mt-16 grid max-w-5xl gap-8 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-8">
            <h2 className="text-xl font-semibold text-white">For construction companies</h2>
            <ul className="mt-5 space-y-3 text-sm text-slate-400">
              <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Search suppliers by category and coverage area</li>
              <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Connect, then invite them straight into your existing RFQs</li>
              <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Award and receive goods through your normal ERP workflow -- no second system</li>
            </ul>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-8">
            <h2 className="text-xl font-semibold text-white">For suppliers</h2>
            <ul className="mt-5 space-y-3 text-sm text-slate-400">
              <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Apply once, get reviewed, get verified</li>
              <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Your own free Supplier Portal -- manage your catalog, team, and quotations</li>
              <li className="flex gap-2"><CheckCircle2 className="h-5 w-5 shrink-0 text-blue-400" />Pay commission only on the orders you actually win, under your own agreed terms</li>
            </ul>
            <Link href="/become-a-supplier" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-blue-400 hover:text-blue-300">
              Apply to become a supplier <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        <div className="mx-auto mt-16 max-w-3xl rounded-2xl border border-white/10 bg-slate-900 p-8 text-center">
          <Truck className="mx-auto h-8 w-8 text-blue-400" />
          <p className="mt-4 text-slate-300">Nothing a supplier submits is automatically verified or connected -- every application and every connection is reviewed by our team first.</p>
        </div>
      </section>
      <MarketingFooter />
    </div>
  );
}
