"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { label: "Overview", href: "/platform-admin/commissions" },
  { label: "Agreements", href: "/platform-admin/commissions/agreements" },
  { label: "Ledger", href: "/platform-admin/commissions/ledger" },
  { label: "Invoices", href: "/platform-admin/commissions/invoices" },
  { label: "Disputes", href: "/platform-admin/commissions/disputes" },
  { label: "Revenue", href: "/platform-admin/commissions/revenue" },
];

export function CommissionsSubNav() {
  const pathname = usePathname();
  return (
    <div className="flex flex-wrap gap-1 rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-1.5 shadow-[var(--bo-shadow-card)]">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              active ? "bg-[var(--bo-nav-active)] text-[var(--bo-text)]" : "text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
