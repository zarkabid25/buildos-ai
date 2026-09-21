import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type {
  Attendance,
  AttendanceStatus,
  Employee,
  Equipment,
  EquipmentStatus,
  MaintenanceReminder,
} from "@/lib/workforce-types";

export function useEmployees() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["employees"],
    queryFn: () => api.get<Employee[]>("/employees", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateEmployee() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { full_name: string; designation?: string; daily_wage: string }) =>
      api.post<Employee>("/employees", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["employees"] }),
  });
}

export function useRecordAttendance() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      employee_id: string;
      project_id: string;
      attendance_date: string;
      status: AttendanceStatus;
    }) => api.post<Attendance>("/attendance", input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attendance"] });
      queryClient.invalidateQueries({ queryKey: ["labor-cost"] });
    },
  });
}

export function useEquipmentList() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["equipment"],
    queryFn: () => api.get<Equipment[]>("/equipment", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useCreateEquipment() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; equipment_type?: string }) =>
      api.post<Equipment>("/equipment", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["equipment"] }),
  });
}

export function useUpdateEquipmentStatus() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: EquipmentStatus }) =>
      api.patch<Equipment>(`/equipment/${id}`, { status }, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["equipment"] }),
  });
}

export function useMaintenanceReminders() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["equipment", "reminders"],
    queryFn: () => api.get<MaintenanceReminder[]>("/equipment/reminders", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useAddMaintenanceRecord() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      equipmentId,
      ...input
    }: {
      equipmentId: string;
      maintenance_date: string;
      description?: string;
      cost?: string;
      next_due_date?: string;
    }) => api.post(`/equipment/${equipmentId}/maintenance`, input, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["equipment"] });
    },
  });
}
