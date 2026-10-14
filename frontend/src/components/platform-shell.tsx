"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/platform-admin/dashboard" },
  { label: "Companies", href: "/platform-admin/companies" },
];

export function PlatformShell({ children }: { children: ReactNode }) {
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
    <div className="flex h-screen w-full">
      {navOpen && (
        <div aria-hidden className="fixed inset-0 z-30 bg-black/30 md:hidden" onClick={() => setNavOpen(false)} />
      )}
      <aside
        id="platform-sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col bg-sidebar text-gray-300 transition-transform md:static md:translate-x-0",
          navOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <span className="text-lg font-semibold text-white">BuildOS Platform</span>
          <button
            aria-label="Close menu"
            className="rounded p-1 text-gray-400 hover:text-white md:hidden"
            onClick={() => setNavOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block rounded-md px-2 py-1.5 text-sm",
                pathname === item.href ? "bg-white/10 text-white" : "text-gray-300 hover:bg-white/5 hover:text-white"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center justify-between gap-3 border-b border-border bg-surface px-4 md:px-6">
          <button
            aria-label="Open menu"
            aria-controls="platform-sidebar"
            aria-expanded={navOpen}
            className="rounded p-1 text-muted hover:text-ink md:hidden"
            onClick={() => setNavOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex-1" />
          <div className="flex shrink-0 items-center gap-3">
            <span className="hidden text-sm font-medium sm:inline">{admin?.full_name ?? ""}</span>
            <button onClick={handleLogout} className="text-sm text-muted hover:text-ink">
              Log out
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto bg-background p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
