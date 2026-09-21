"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth-context";
import {
  useCreateEquipment,
  useEquipmentList,
  useMaintenanceReminders,
  useUpdateEquipmentStatus,
} from "@/lib/use-workforce";
import type { EquipmentStatus } from "@/lib/workforce-types";

const STATUS_OPTIONS: EquipmentStatus[] = ["available", "in_use", "maintenance", "retired"];
const STATUS_CLASSES: Record<EquipmentStatus, string> = {
  available: "bg-green-100 text-green-700",
  in_use: "bg-blue-100 text-blue-700",
  maintenance: "bg-amber-100 text-amber-700",
  retired: "bg-gray-100 text-gray-700",
};

export default function EquipmentPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const { data: equipmentList } = useEquipmentList();
  const { data: reminders } = useMaintenanceReminders();
  const createEquipment = useCreateEquipment();
  const updateStatus = useUpdateEquipmentStatus();

  const [form, setForm] = useState({ name: "", equipment_type: "" });

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  async function handleAdd() {
    if (!form.name) return;
    await createEquipment.mutateAsync(form);
    setForm({ name: "", equipment_type: "" });
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Equipment</h1>
          <p className="text-muted">Machinery, tools and their maintenance schedule.</p>
        </div>

        {reminders && reminders.length > 0 && (
          <Card className="border-warning/40 bg-amber-50/40">
            <h2 className="mb-2 text-sm font-semibold text-ink">🔧 Maintenance Reminders</h2>
            <ul className="space-y-1 text-sm">
              {reminders.map((r) => (
                <li key={r.equipment_id} className={r.is_overdue ? "font-medium text-danger" : "text-ink"}>
                  {r.equipment_name} — {r.is_overdue ? `overdue by ${-r.days_until_due} day(s)` : `due in ${r.days_until_due} day(s)`}
                </li>
              ))}
            </ul>
          </Card>
        )}

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink">Add equipment</h2>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input
              placeholder="Type (e.g. Excavator)"
              value={form.equipment_type}
              onChange={(e) => setForm({ ...form, equipment_type: e.target.value })}
            />
            <Button onClick={handleAdd} disabled={createEquipment.isPending}>
              Add equipment
            </Button>
          </div>
        </Card>

        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {(!equipmentList || equipmentList.length === 0) && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-sm text-muted">
                    No equipment yet.
                  </td>
                </tr>
              )}
              {equipmentList?.map((eq) => (
                <tr key={eq.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-medium text-ink">{eq.name}</td>
                  <td className="px-4 py-3 text-muted">{eq.equipment_type ?? "—"}</td>
                  <td className="px-4 py-3">
                    <select
                      className={`h-7 rounded-full border-0 px-2 text-xs font-medium ${STATUS_CLASSES[eq.status]}`}
                      value={eq.status}
                      onChange={(e) =>
                        updateStatus.mutate({ id: eq.id, status: e.target.value as EquipmentStatus })
                      }
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s.replace("_", " ")}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </AppShell>
  );
}
