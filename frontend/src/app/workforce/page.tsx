"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, QueryView } from "@/components/ui/states";
import { useAuth } from "@/lib/auth-context";
import { useProjects } from "@/lib/use-projects";
import { useCreateEmployee, useEmployees, useRecordAttendance } from "@/lib/use-workforce";
import { attempt, formatCurrency, localToday } from "@/lib/utils";
import type { AttendanceStatus } from "@/lib/workforce-types";

const ATTENDANCE_OPTIONS: AttendanceStatus[] = ["present", "absent", "half_day", "leave"];

export default function WorkforcePage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const employeesQuery = useEmployees();
  const employees = employeesQuery.data;
  const { toast } = useFeedback();
  const { data: projects } = useProjects();
  const createEmployee = useCreateEmployee();
  const recordAttendance = useRecordAttendance();

  const [empForm, setEmpForm] = useState({ full_name: "", designation: "", daily_wage: "" });
  const [attForm, setAttForm] = useState({
    employee_id: "",
    project_id: "",
    attendance_date: localToday(),
    status: "present" as AttendanceStatus,
  });

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) return null;

  async function handleAddEmployee() {
    if (!empForm.full_name) return;
    if (!(await attempt(createEmployee.mutateAsync(empForm)))) return;
    setEmpForm({ full_name: "", designation: "", daily_wage: "" });
  }

  async function handleRecordAttendance() {
    if (!attForm.employee_id || !attForm.project_id) return;
    if (!(await attempt(recordAttendance.mutateAsync(attForm)))) return;
    toast("Attendance recorded.", "success");
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

        <QueryView
          query={employeesQuery}
          isEmpty={(list) => list.length === 0}
          empty={<EmptyState title="No employees yet" hint="Add people above to assign them and record attendance." />}
        >
          {(employeeList) => (
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
                  {employeeList.map((emp) => (
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
          )}
        </QueryView>
      </div>
    </AppShell>
  );
}
