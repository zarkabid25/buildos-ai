import type { Metadata } from "next";
import { Building2, Network, ShieldCheck } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";

export const metadata: Metadata = {
  title: "About — BuildOS AI",
  description: "BuildOS AI is building an AI-native construction ERP and a verified supplier marketplace, in one system.",
};

export default function AboutPage() {
  return (
    <div className="bg-slate-950">
      <MarketingNav />
      <section className="px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <h1 className="text-4xl font-bold text-white sm:text-5xl">About BuildOS AI</h1>
          <p className="mt-6 text-lg text-slate-400">
            Construction companies run on spreadsheets stitched together after the fact, and suppliers are found through word of mouth. BuildOS AI brings both into one system: a real construction ERP for projects, procurement and inventory, and a verified supplier marketplace connected directly into it.
          </p>
          <p className="mt-4 text-lg text-slate-400">
            Every subscription, commission, and AI-drafted proposal in BuildOS AI follows the same principle: a human approves before anything financial or inventory-related is actually committed.
          </p>
        </div>

        <div className="mx-auto mt-16 grid max-w-4xl gap-8 sm:grid-cols-3">
          {[
            { icon: Building2, title: "One ERP", desc: "Projects, cost control, procurement and inventory in a single system." },
            { icon: Network, title: "A verified marketplace", desc: "Every supplier is reviewed and verified before a company can connect." },
            { icon: ShieldCheck, title: "Strict isolation", desc: "Every company's data is its own -- never shared with another tenant or supplier." },
          ].map((v) => (
            <div key={v.title} className="rounded-2xl border border-white/10 bg-slate-900/50 p-6 text-center">
              <v.icon className="mx-auto h-8 w-8 text-blue-400" />
              <h3 className="mt-4 text-base font-semibold text-white">{v.title}</h3>
              <p className="mt-2 text-sm text-slate-400">{v.desc}</p>
            </div>
          ))}
        </div>
      </section>
      <MarketingFooter />
    </div>
  );
}
