"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { GlobalSearch } from "@/components/global-search";
import { NotificationBell } from "@/components/notification-bell";
import { useAuth } from "@/lib/auth-context";
import { useCompany } from "@/lib/use-settings";
import { cn, setDisplayCurrency } from "@/lib/utils";

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
      { label: "BOQ", href: "/boq" },
      { label: "Tasks", href: "/tasks" },
      { label: "Schedule", href: "/schedule" },
      { label: "Daily Reports", href: "/daily-reports" },
    ],
  },
  {
    label: "Supply Chain",
    items: [
      { label: "Inventory", href: "/inventory" },
      { label: "Warehouses", href: "/inventory" },
      { label: "Suppliers", href: "/suppliers" },
      { label: "Material Requests", href: "/procurement" },
      { label: "Purchase Orders", href: "/procurement" },
    ],
  },
  {
    label: "Cost Control",
    items: [
      { label: "Budgets", href: "/budgets" },
      { label: "Expenses", href: "/expenses" },
      { label: "Project Costs", href: "/project-costs" },
    ],
  },
  {
    label: "Operations",
    items: [
      { label: "Workforce", href: "/workforce" },
      { label: "Equipment", href: "/equipment" },
    ],
  },
  { label: "Documents", href: "/documents" },
  { label: "Reports", href: "/reports" },
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
  const { data: company } = useCompany();
  const currency = company?.currency ?? "PKR";
  // Set during render (not in an effect) so the pages below format amounts with
  // it on this same pass; the content is keyed on it below so a change re-renders them.
  setDisplayCurrency(currency);

  // Below md the sidebar is a drawer (BUILD-113); close it whenever the route changes.
  const [navOpen, setNavOpen] = useState(false);
  useEffect(() => setNavOpen(false), [pathname]);
  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setNavOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navOpen]);

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <div className="flex h-screen w-full">
      {navOpen && (
        <div aria-hidden className="fixed inset-0 z-30 bg-black/30 md:hidden" onClick={() => setNavOpen(false)} />
      )}
      <aside
        id="app-sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col bg-sidebar text-gray-300 transition-transform md:static md:translate-x-0",
          navOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <span className="text-lg font-semibold text-white">BuildOS AI</span>
          <button
            aria-label="Close menu"
            className="rounded p-1 text-gray-400 hover:text-white md:hidden"
            onClick={() => setNavOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
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
          <NavRow label="Settings" href="/settings" active={pathname === "/settings"} />
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center justify-between gap-3 border-b border-border bg-surface px-4 md:px-6">
          <button
            aria-label="Open menu"
            aria-controls="app-sidebar"
            aria-expanded={navOpen}
            className="rounded p-1 text-muted hover:text-ink md:hidden"
            onClick={() => setNavOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <GlobalSearch />
          <div className="flex shrink-0 items-center gap-3">
            <NotificationBell />
            <span className="hidden text-sm font-medium sm:inline">{user?.full_name ?? ""}</span>
            <button onClick={handleLogout} className="text-sm text-muted hover:text-ink">
              Log out
            </button>
          </div>
        </header>
        <main key={currency} className="flex-1 overflow-y-auto bg-background p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
