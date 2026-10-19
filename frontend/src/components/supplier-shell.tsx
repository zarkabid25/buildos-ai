"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ClipboardList, FileText, LayoutDashboard, LifeBuoy, Menu, Package, Percent, ShoppingCart, User, X } from "lucide-react";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/supplier-portal", icon: LayoutDashboard },
  { label: "Products", href: "/supplier-portal/products", icon: Package },
  { label: "RFQs", href: "/supplier-portal/rfqs", icon: ClipboardList },
  { label: "Quotations", href: "/supplier-portal/quotations", icon: FileText },
  { label: "Orders", href: "/supplier-portal/orders", icon: ShoppingCart },
  { label: "Commissions", href: "/supplier-portal/commissions", icon: Percent },
  { label: "Support", href: "/supplier-portal/support", icon: LifeBuoy },
  { label: "Profile", href: "/supplier-portal/profile", icon: User },
];

export function SupplierShell({ children, breadcrumb }: { children: ReactNode; breadcrumb: string }) {
  const { user, activeMembership, logout } = useSupplierAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);
  useEffect(() => setNavOpen(false), [pathname]);

  function handleLogout() {
    logout();
    router.push("/supplier-portal/login");
  }

  return (
    <div className="flex h-screen w-full bg-gray-50">
      {navOpen && <div aria-hidden className="fixed inset-0 z-30 bg-black/20 lg:hidden" onClick={() => setNavOpen(false)} />}
      <aside
        id="supplier-sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r border-gray-200 bg-white transition-transform lg:static lg:translate-x-0",
          navOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <span className="text-lg font-semibold tracking-tight text-gray-900">Supplier Portal</span>
          <button aria-label="Close menu" className="rounded p-1 text-gray-400 hover:text-gray-900 lg:hidden" onClick={() => setNavOpen(false)}>
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || (item.href !== "/supplier-portal" && pathname.startsWith(`${item.href}/`));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors",
                  active ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-gray-100"
                )}
              >
                <Icon className={cn("h-[18px] w-[18px]", active ? "text-blue-600" : "text-gray-400")} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-gray-200 p-3">
          {activeMembership && (
            <div className="mb-2 rounded-lg bg-teal-50 px-3 py-2">
              <p className="truncate text-xs font-medium text-teal-800">{activeMembership.marketplace_supplier_name}</p>
              <p className="text-[11px] capitalize text-teal-600">{activeMembership.role}</p>
            </div>
          )}
          <div className="flex items-center justify-between rounded-lg px-2 py-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-gray-900">{user?.full_name ?? ""}</p>
              <p className="truncate text-xs text-gray-500">{user?.email ?? ""}</p>
            </div>
            <button onClick={handleLogout} className="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-gray-500 hover:bg-gray-100">
              Log out
            </button>
          </div>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-gray-200 bg-white px-4 lg:px-6">
          <button
            aria-label="Open menu"
            aria-controls="supplier-sidebar"
            aria-expanded={navOpen}
            className="rounded p-2 text-gray-500 hover:text-gray-900 lg:hidden"
            onClick={() => setNavOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
          <span className="rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700">{breadcrumb}</span>
        </header>
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
