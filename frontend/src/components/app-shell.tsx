import type { ReactNode } from "react";

const NAV_SECTIONS = [
  { label: "AI Command Center", href: "/ai" },
  { label: "Dashboard", href: "/dashboard" },
  {
    label: "Construction",
    items: ["Projects", "BOQ", "Tasks", "Schedule", "Daily Reports"],
  },
  {
    label: "Supply Chain",
    items: ["Inventory", "Warehouses", "Suppliers", "Material Requests", "Purchase Orders"],
  },
  {
    label: "Cost Control",
    items: ["Budgets", "Expenses", "Project Costs"],
  },
  {
    label: "Operations",
    items: ["Workforce", "Equipment"],
  },
  { label: "Documents", href: "/documents" },
  { label: "AI Insights", href: "/ai-insights" },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen w-full">
      <aside className="flex w-64 flex-col bg-sidebar text-gray-300">
        <div className="px-5 py-5 text-lg font-semibold text-white">BuildOS AI</div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3">
          {NAV_SECTIONS.map((section) =>
            "items" in section ? (
              <div key={section.label} className="pt-3">
                <div className="px-2 pb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
                  {section.label}
                </div>
                {section.items.map((item) => (
                  <div
                    key={item}
                    className="rounded-md px-2 py-1.5 text-sm hover:bg-white/5 hover:text-white"
                  >
                    {item}
                  </div>
                ))}
              </div>
            ) : (
              <div
                key={section.label}
                className="rounded-md px-2 py-1.5 text-sm font-medium hover:bg-white/5 hover:text-white"
              >
                {section.label}
              </div>
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
          <div className="text-sm font-medium">Zark Abid</div>
        </header>
        <main className="flex-1 overflow-y-auto bg-background p-6">{children}</main>
      </div>
    </div>
  );
}
