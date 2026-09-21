"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth-context";
import { useProjects } from "@/lib/use-projects";
import { useCreateEmployee, useEmployees, useRecordAttendance } from "@/lib/use-workforce";
import { formatCurrency } from "@/lib/utils";
import type { AttendanceStatus } from "@/lib/workforce-types";

const ATTENDANCE_OPTIONS: AttendanceStatus[] = ["present", "absent", "half_day", "leave"];

export default function WorkforcePage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const { data: employees } = useEmployees();
  const { data: projects } = useProjects();
  const createEmployee = useCreateEmployee();
  const recordAttendance = useRecordAttendance();

  const [empForm, setEmpForm] = useState({ full_name: "", designation: "", daily_wage: "" });
  const [attForm, setAttForm] = useState({
    employee_id: "",
    project_id: "",
    attendance_date: new Date().toISOString().slice(0, 10),
    status: "present" as AttendanceStatus,
  });

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  async function handleAddEmployee() {
    if (!empForm.full_name) return;
    await createEmployee.mutateAsync(empForm);
    setEmpForm({ full_name: "", designation: "", daily_wage: "" });
  }

  async function handleRecordAttendance() {
    if (!attForm.employee_id || !attForm.project_id) return;
    await recordAttendance.mutateAsync(attForm);
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Workforce</h1>
          <p className="text-muted">Employees, project assignments and attendance.</p>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink">Add employee</h2>
            <div className="space-y-2">
              <Input
                placeholder="Full name"
                value={empForm.full_name}
                onChange={(e) => setEmpForm({ ...empForm, full_name: e.target.value })}
              />
              <Input
                placeholder="Designation (e.g. Mason)"
                value={empForm.designation}
                onChange={(e) => setEmpForm({ ...empForm, designation: e.target.value })}
              />
              <Input
                type="number"
                placeholder="Daily wage"
                value={empForm.daily_wage}
                onChange={(e) => setEmpForm({ ...empForm, daily_wage: e.target.value })}
              />
              <Button onClick={handleAddEmployee} disabled={createEmployee.isPending} className="w-full">
                Add employee
              </Button>
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink">Record attendance</h2>
            <div className="space-y-2">
              <select
                className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
                value={attForm.employee_id}
                onChange={(e) => setAttForm({ ...attForm, employee_id: e.target.value })}
              >
                <option value="">Employee...</option>
                {employees?.map((emp) => (
                  <option key={emp.id} value={emp.id}>{emp.full_name}</option>
                ))}
              </select>
              <select
                className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
                value={attForm.project_id}
                onChange={(e) => setAttForm({ ...attForm, project_id: e.target.value })}
              >
                <option value="">Project...</option>
                {projects?.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="date"
                  value={attForm.attendance_date}
                  onChange={(e) => setAttForm({ ...attForm, attendance_date: e.target.value })}
                />
                <select
                  className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
                  value={attForm.status}
                  onChange={(e) => setAttForm({ ...attForm, status: e.target.value as AttendanceStatus })}
                >
                  {ATTENDANCE_OPTIONS.map((s) => (
                    <option key={s} value={s}>{s.replace("_", " ")}</option>
                  ))}
                </select>
              </div>
              <Button onClick={handleRecordAttendance} disabled={recordAttendance.isPending} className="w-full">
                Record
              </Button>
            </div>
          </Card>
        </div>

        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Designation</th>
                <th className="px-4 py-3 font-medium">Daily Wage</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {(!employees || employees.length === 0) && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-sm text-muted">
                    No employees yet.
                  </td>
                </tr>
              )}
              {employees?.map((emp) => (
                <tr key={emp.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-medium text-ink">{emp.full_name}</td>
                  <td className="px-4 py-3 text-muted">{emp.designation ?? "—"}</td>
                  <td className="px-4 py-3 text-ink">{formatCurrency(emp.daily_wage)}</td>
                  <td className="px-4 py-3 text-muted">{emp.is_active ? "Active" : "Inactive"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </AppShell>
  );
}
