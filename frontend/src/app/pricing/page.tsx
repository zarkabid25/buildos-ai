"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { usePublicPlans } from "@/lib/use-public";

export default function PricingPage() {
  const { data: plans, isLoading, isError } = usePublicPlans();
  const [period, setPeriod] = useState<"monthly" | "annual">("monthly");

  return (
    <div className="bg-slate-950">
      <MarketingNav />
      <section className="px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold text-white sm:text-5xl">Plans that scale with your projects</h1>
          <p className="mt-5 text-lg text-slate-400">Real pricing, configured by our team -- never hardcoded on this page.</p>
          <div className="mt-8 inline-flex rounded-lg border border-white/10 p-1">
            <button onClick={() => setPeriod("monthly")} className={`rounded-md px-4 py-1.5 text-sm font-medium ${period === "monthly" ? "bg-white text-slate-900" : "text-slate-300"}`}>Monthly</button>
            <button onClick={() => setPeriod("annual")} className={`rounded-md px-4 py-1.5 text-sm font-medium ${period === "annual" ? "bg-white text-slate-900" : "text-slate-300"}`}>Annual</button>
          </div>
        </div>

        {isLoading && <p className="mt-16 text-center text-slate-400">Loading plans...</p>}
        {isError && <p className="mt-16 text-center text-slate-400">Pricing is temporarily unavailable -- please check back shortly or contact us.</p>}
        {plans && plans.length === 0 && <p className="mt-16 text-center text-slate-400">Pricing isn't published yet -- request a demo and we'll walk you through it.</p>}

        {plans && plans.length > 0 && (
          <div className="mx-auto mt-16 grid max-w-6xl gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {plans.map((plan) => {
              const price = plan.prices.find((p) => p.billing_period === period && p.is_current);
              return (
                <div key={plan.id} className="rounded-2xl border border-white/10 bg-slate-900/50 p-8">
                  <h2 className="text-xl font-semibold text-white">{plan.name}</h2>
                  {plan.description && <p className="mt-2 text-sm text-slate-400">{plan.description}</p>}
                  <p className="mt-6 text-4xl font-bold text-white">
                    {price ? `${price.amount} ${price.currency}` : "Contact us"}
                    {price && <span className="text-base font-normal text-slate-400">/{period === "monthly" ? "mo" : "yr"}</span>}
                  </p>
                  {plan.trial_days > 0 && <p className="mt-2 text-sm text-blue-400">{plan.trial_days}-day free trial</p>}
                  <ul className="mt-6 space-y-2 text-sm text-slate-300">
                    <li className="flex gap-2"><Check className="h-4 w-4 text-blue-400" />{plan.max_projects != null ? `${plan.max_projects} projects` : "Unlimited projects"}</li>
                    <li className="flex gap-2"><Check className="h-4 w-4 text-blue-400" />{plan.max_team_members != null ? `${plan.max_team_members} team members` : "Unlimited team members"}</li>
                    <li className="flex gap-2"><Check className="h-4 w-4 text-blue-400" />{plan.marketplace_included ? "Supplier marketplace included" : "Core ERP"}</li>
                  </ul>
                  <Link href="/register" className="mt-8 flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-500">
                    Start free trial <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </section>
      <MarketingFooter />
    </div>
  );
}
