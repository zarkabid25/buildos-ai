import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// The signed-in company's currency (BUILD-106). Set once by AppShell when the
// company loads, so the many formatCurrency call sites don't each need it passed in.
let displayCurrency = "PKR";

export function setDisplayCurrency(currency: string) {
  displayCurrency = currency;
}

export function formatCurrency(value: string | number, currency = displayCurrency) {
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return `${currency} 0`;
  if (Math.abs(n) >= 1_000_000) return `${currency} ${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${currency} ${(n / 1_000).toFixed(1)}K`;
  return `${currency} ${n.toFixed(0)}`;
}

/** Full amount with thousands separators, e.g. "PKR 1,805,000.50". Use where amounts are
 *  compared or reconciled (quotes, payments); formatCurrency's 1.8M style hides differences. */
export function formatMoney(value: string | number, currency = displayCurrency) {
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return `${currency} 0`;
  const hasCents = Math.round(n * 100) % 100 !== 0;
  return `${currency} ${n.toLocaleString("en-US", { minimumFractionDigits: hasCents ? 2 : 0, maximumFractionDigits: 2 })}`;
}

export const STATUS_LABELS: Record<string, string> = {
  planning: "Planning",
  active: "Active",
  on_hold: "On Hold",
  completed: "Completed",
  cancelled: "Cancelled",
};

export const STATUS_CLASSES: Record<string, string> = {
  planning: "bg-gray-100 text-gray-700",
  active: "bg-green-100 text-green-700",
  on_hold: "bg-amber-100 text-amber-700",
  completed: "bg-blue-100 text-blue-700",
  cancelled: "bg-red-100 text-red-700",
};

// For `await mutation.mutateAsync(...)` in event handlers: resolves to undefined
// on failure instead of throwing. The global mutation handler (lib/providers.tsx)
// has already shown the error, so the caller only needs to stop.
export async function attempt<T>(promise: Promise<T>): Promise<T | undefined> {
  try {
    return await promise;
  } catch {
    return undefined;
  }
}

/** Today's date as YYYY-MM-DD in the user's own timezone. (toISOString() gives the
 *  UTC date, which is a day behind for the first hours of the day east of UTC.) */
export function localToday(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
