"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { Building2, CalendarClock, LayoutGrid, ListChecks, Menu, Search, Users2, Users, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { cn } from "@/lib/utils";

// Only destinations that actually exist. Epic 27's remaining items (Suppliers,
// RFQs, Commissions, Revenue Reports...) all need backend that isn't built yet
// -- see docs/tickets.md -- so they aren't shown as dead links here.
const NAV_ITEMS = [
  { label: "Overview", href: "/platform-admin/dashboard", icon: LayoutGrid },
  { label: "Companies", href: "/platform-admin/companies", icon: Building2 },
  { label: "CRM", href: "/platform-admin/crm", icon: Users2 },
  { label: "Follow-ups", href: "/platform-admin/crm/follow-ups", icon: CalendarClock },
  { label: "Staff", href: "/platform-admin/staff", icon: Users },
  { label: "Audit Log", href: "/platform-admin/audit", icon: ListChecks },
];

export function PlatformShell({ children, breadcrumb }: { children: ReactNode; breadcrumb: string }) {
  const { admin, logout } = usePlatformAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [navOpen, setNavOpen] = useState(false);
  useEffect(() => setNavOpen(false), [pathname]);

  function handleLogout() {
    logout();
    router.push("/platform-admin/login");
  }

  return (
    <div className="buildos-admin flex h-screen w-full">
      {navOpen && (
        <div aria-hidden className="fixed inset-0 z-30 bg-black/20 lg:hidden" onClick={() => setNavOpen(false)} />
      )}
      <aside
        id="platform-sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r border-[var(--bo-border)] bg-[var(--bo-surface)] transition-transform lg:static lg:translate-x-0",
          navOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <span className="text-lg font-semibold tracking-[-0.025em] text-[var(--bo-text)]">BuildOS AI</span>
          <button
            aria-label="Close menu"
            className="rounded p-1 text-[var(--bo-text-muted)] hover:text-[var(--bo-text)] lg:hidden"
            onClick={() => setNavOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-3 pb-3">
          <label htmlFor="platform-search" className="sr-only">
            Search companies
          </label>
          <div className="flex items-center gap-2 rounded-md border border-[var(--bo-border)] px-2.5 py-2">
            <Search className="h-4 w-4 text-[var(--bo-text-muted)]" />
            <input
              id="platform-search"
              type="search"
              placeholder="Search companies..."
              disabled
              title="Coming soon"
              className="w-full bg-transparent text-sm text-[var(--bo-text)] placeholder:text-[var(--bo-text-muted)] focus:outline-none disabled:cursor-not-allowed"
            />
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          <div className="px-2 pb-1 text-xs font-medium text-[var(--bo-text-muted)]">Workspace</div>
          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/platform-admin/crm"
                ? pathname === item.href || (pathname.startsWith(item.href) && !pathname.startsWith("/platform-admin/crm/follow-ups"))
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-10 items-center gap-2.5 rounded-lg px-2.5 text-sm transition-colors",
                  active
                    ? "bg-[var(--bo-nav-active)] font-medium text-[var(--bo-text)]"
                    : "text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]"
                )}
              >
                <Icon className={cn("h-[18px] w-[18px]", active ? "text-[var(--bo-primary)]" : "text-[var(--bo-text-muted)]")} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-[var(--bo-divider)] p-3">
          <div className="flex items-center justify-between rounded-lg px-2 py-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-[var(--bo-text)]">{admin?.full_name ?? ""}</p>
              <p className="truncate text-xs text-[var(--bo-text-muted)]">{admin?.email ?? ""}</p>
            </div>
            <button
              onClick={handleLogout}
              className="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]"
            >
              Log out
            </button>
          </div>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-[var(--bo-border)] bg-[var(--bo-surface)] px-4 lg:px-6">
          <button
            aria-label="Open menu"
            aria-controls="platform-sidebar"
            aria-expanded={navOpen}
            className="rounded p-1 text-[var(--bo-text-muted)] hover:text-[var(--bo-text)] lg:hidden"
            onClick={() => setNavOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="rounded-md bg-[var(--bo-nav-active)] px-2.5 py-1 text-sm font-medium text-[var(--bo-text-secondary)]">
            {breadcrumb}
          </span>
        </header>
        <main className="flex-1 overflow-y-auto bg-[var(--bo-canvas)] p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
