import Link from "next/link";
import type { Metadata } from "next";
import { ArrowRight, LifeBuoy, Truck, Users } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";

export const metadata: Metadata = {
  title: "Contact — BuildOS AI",
  description: "Get in touch with BuildOS AI -- request a demo, apply as a supplier, or get support.",
};

export default function ContactPage() {
  return (
    <div className="bg-slate-950">
      <MarketingNav />
      <section className="px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold text-white sm:text-5xl">Get in touch</h1>
          <p className="mt-5 text-lg text-slate-400">Choose what you need below -- each goes to the right team.</p>
        </div>

        <div className="mx-auto mt-16 grid max-w-4xl gap-8 sm:grid-cols-3">
          <Link href="/request-demo" className="rounded-2xl border border-white/10 bg-slate-900/50 p-6 text-center transition-colors hover:border-blue-400/50">
            <Users className="mx-auto h-8 w-8 text-blue-400" />
            <h3 className="mt-4 text-base font-semibold text-white">Request a demo</h3>
            <p className="mt-2 text-sm text-slate-400">See BuildOS AI for your construction company.</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-blue-400">Request demo <ArrowRight className="h-3.5 w-3.5" /></span>
          </Link>
          <Link href="/become-a-supplier" className="rounded-2xl border border-white/10 bg-slate-900/50 p-6 text-center transition-colors hover:border-blue-400/50">
            <Truck className="mx-auto h-8 w-8 text-blue-400" />
            <h3 className="mt-4 text-base font-semibold text-white">Become a supplier</h3>
            <p className="mt-2 text-sm text-slate-400">Apply to join the verified supplier network.</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-blue-400">Apply now <ArrowRight className="h-3.5 w-3.5" /></span>
          </Link>
          <Link href="/login" className="rounded-2xl border border-white/10 bg-slate-900/50 p-6 text-center transition-colors hover:border-blue-400/50">
            <LifeBuoy className="mx-auto h-8 w-8 text-blue-400" />
            <h3 className="mt-4 text-base font-semibold text-white">Already a customer?</h3>
            <p className="mt-2 text-sm text-slate-400">Sign in and open a support ticket from your portal.</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-blue-400">Sign in <ArrowRight className="h-3.5 w-3.5" /></span>
          </Link>
        </div>
      </section>
      <MarketingFooter />
    </div>
  );
}
