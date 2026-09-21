"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

type NavItem = { label: string; href: string | null };
type NavLink = { label: string; href: string; items?: undefined };
type NavGroup = { label: string; items: NavItem[]; href?: undefined };
type NavEntry = NavLink | NavGroup;

// href: null means the module isn't built yet — rendered as a disabled label
// rather than a dead link, so the sidebar still communicates the full IA.
const NAV_SECTIONS: NavEntry[] = [
  { label: "AI Command Center", href: "/ai" },
  { label: "Dashboard", href: "/dashboard" },
  {
    label: "Construction",
    items: [
      { label: "Projects", href: "/projects" },
      { label: "BOQ", href: null },
      { label: "Tasks", href: null },
      { label: "Schedule", href: null },
      { label: "Daily Reports", href: null },
    ],
  },
  {
    label: "Supply Chain",
    items: [
      { label: "Inventory", href: "/inventory" },
      { label: "Warehouses", href: "/inventory" },
      { label: "Suppliers", href: "/suppliers" },
      { label: "Material Requests", href: null },
      { label: "Purchase Orders", href: null },
    ],
  },
  {
    label: "Cost Control",
    items: [
      { label: "Budgets", href: null },
      { label: "Expenses", href: null },
      { label: "Project Costs", href: null },
    ],
  },
  {
    label: "Operations",
    items: [
      { label: "Workforce", href: null },
      { label: "Equipment", href: null },
    ],
  },
  { label: "Documents", href: "/documents" },
  { label: "AI Insights", href: "/ai-insights" },
];

function NavRow({ label, href, active }: { label: string; href: string | null; active: boolean }) {
  const classes = cn(
    "block rounded-md px-2 py-1.5 text-sm",
    active ? "bg-white/10 text-white" : "text-gray-300 hover:bg-white/5 hover:text-white",
    !href && "cursor-default text-gray-600 hover:bg-transparent hover:text-gray-600"
  );

  if (!href) {
    return <div className={classes}>{label}</div>;
  }
  return (
    <Link href={href} className={classes}>
      {label}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <div className="flex h-screen w-full">
      <aside className="flex w-64 flex-col bg-sidebar text-gray-300">
        <div className="px-5 py-5 text-lg font-semibold text-white">BuildOS AI</div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3">
          {NAV_SECTIONS.map((section) =>
            section.items ? (
              <div key={section.label} className="pt-3">
                <div className="px-2 pb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
                  {section.label}
                </div>
                {section.items.map((item) => (
                  <NavRow
                    key={item.label}
                    label={item.label}
                    href={item.href}
                    active={item.href === pathname}
                  />
                ))}
              </div>
            ) : (
              <NavRow
                key={section.label}
                label={section.label}
                href={section.href}
                active={section.href === pathname}
              />
            )
          )}
        </nav>
        <div className="border-t border-white/10 px-3 py-3">
          <div className="rounded-md px-2 py-1.5 text-sm hover:bg-white/5 hover:text-white">
            Settings
          </div>
        </div>
      </aside>
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-6">
          <div className="text-sm text-muted">Search...</div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">{user?.full_name ?? ""}</span>
            <button onClick={handleLogout} className="text-sm text-muted hover:text-ink">
              Log out
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto bg-background p-6">{children}</main>
      </div>
    </div>
  );
}
