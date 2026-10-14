export function StatusBadge({ active, activeLabel = "Active", inactiveLabel = "Suspended" }: {
  active: boolean;
  activeLabel?: string;
  inactiveLabel?: string;
}) {
  return (
    <span
      className={
        active
          ? "rounded-full bg-[var(--bo-success-bg)] px-2 py-0.5 text-xs font-medium text-[var(--bo-success)]"
          : "rounded-full bg-[var(--bo-danger-bg)] px-2 py-0.5 text-xs font-medium text-[var(--bo-danger)]"
      }
    >
      {active ? activeLabel : inactiveLabel}
    </span>
  );
}
