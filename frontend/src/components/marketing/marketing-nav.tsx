"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";

const LINKS = [
  { label: "Features", href: "/features" },
  { label: "Construction ERP", href: "/construction-erp" },
  { label: "Supplier Network", href: "/supplier-network" },
  { label: "Pricing", href: "/pricing" },
  { label: "About", href: "/about" },
  { label: "Contact", href: "/contact" },
];

export function MarketingNav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="text-lg font-semibold tracking-tight text-white">
          BuildOS <span className="text-blue-400">AI</span>
        </Link>
        <nav className="hidden items-center gap-8 lg:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="text-sm font-medium text-slate-300 transition-colors hover:text-white">
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="hidden items-center gap-3 lg:flex">
          <Link href="/login" className="text-sm font-medium text-slate-300 hover:text-white">Sign in</Link>
          <Link href="/register" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500">
            Start free trial
          </Link>
        </div>
        <button aria-label="Open menu" className="rounded p-2 text-slate-300 lg:hidden" onClick={() => setOpen(true)}>
          <Menu className="h-6 w-6" />
        </button>
      </div>
      {open && (
        <div className="fixed inset-0 z-50 bg-slate-950 lg:hidden">
          <div className="flex h-16 items-center justify-between px-4">
            <span className="text-lg font-semibold text-white">BuildOS AI</span>
            <button aria-label="Close menu" className="rounded p-2 text-slate-300" onClick={() => setOpen(false)}>
              <X className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex flex-col gap-1 px-4 py-4">
            {LINKS.map((l) => (
              <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="rounded-lg px-3 py-3 text-base font-medium text-slate-200 hover:bg-white/5">
                {l.label}
              </Link>
            ))}
            <div className="mt-4 flex flex-col gap-2 border-t border-white/10 pt-4">
              <Link href="/login" onClick={() => setOpen(false)} className="rounded-lg px-3 py-3 text-base font-medium text-slate-200 hover:bg-white/5">Sign in</Link>
              <Link href="/register" onClick={() => setOpen(false)} className="rounded-lg bg-blue-600 px-3 py-3 text-center text-base font-semibold text-white">Start free trial</Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
