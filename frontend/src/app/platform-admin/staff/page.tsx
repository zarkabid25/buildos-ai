"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useFeedback } from "@/components/feedback";
import { PlatformShell } from "@/components/platform-shell";
import { StatusBadge } from "@/components/platform/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type { PlatformStaffRole } from "@/lib/platform-types";
import {
  useCreatePlatformInvitation,
  usePlatformInvitations,
  usePlatformStaff,
  useRevokePlatformInvitation,
  useUpdateStaff,
} from "@/lib/use-platform";

const ROLE_LABELS: Record<PlatformStaffRole, string> = { owner: "Owner", admin: "Admin", support: "Support" };

const inviteSchema = z.object({
  email: z.string().trim().email("Enter a valid email"),
  full_name: z.string().trim().max(255).optional(),
  role: z.enum(["owner", "admin", "support"]),
});
type InviteInput = z.infer<typeof inviteSchema>;

export default function PlatformStaffPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();
  const { toast, confirm } = useFeedback();
  const isOwner = admin?.role === "owner";

  const staffQuery = usePlatformStaff(!!admin);
  const invitationsQuery = usePlatformInvitations(isOwner);
  const createInvitation = useCreatePlatformInvitation();
  const revokeInvitation = useRevokePlatformInvitation();
  const updateStaff = useUpdateStaff();
  const [createdLink, setCreatedLink] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InviteInput>({ resolver: zodResolver(inviteSchema), defaultValues: { role: "admin" } });

  useEffect(() => {
    if (!isLoading && !admin) router.replace("/platform-admin/login");
  }, [isLoading, admin, router]);

  if (isLoading || !admin) return null;

  async function onInvite(values: InviteInput) {
    setCreatedLink(null);
    try {
      const result = await createInvitation.mutateAsync(values);
      const link = `${window.location.origin}/platform-admin/accept-invite?token=${result.token}`;
      setCreatedLink(link);
      reset({ email: "", full_name: "", role: "admin" });
      toast(`Invited ${values.email}.`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleRevoke(id: string, email: string) {
    const ok = await confirm({ title: `Revoke the invitation for ${email}?`, confirmLabel: "Revoke", danger: true });
    if (!ok) return;
    try {
      await revokeInvitation.mutateAsync(id);
      toast("Invitation revoked.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleToggleActive(id: string, name: string, nextActive: boolean) {
    const ok = await confirm({
      title: nextActive ? `Reactivate ${name}?` : `Deactivate ${name}?`,
      body: nextActive ? undefined : "They will no longer be able to sign in.",
      confirmLabel: nextActive ? "Reactivate" : "Deactivate",
      danger: !nextActive,
    });
    if (!ok) return;
    try {
      await updateStaff.mutateAsync({ id, is_active: nextActive });
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  return (
    <PlatformShell breadcrumb="Staff">
      <div className="space-y-5">
        <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
          <h1 className="text-[17px] font-medium text-[var(--bo-text)]">Platform Staff</h1>
          <p className="mt-0.5 text-sm text-[var(--bo-text-muted)]">
            BuildOS's own staff who can sign in to this portal.
          </p>

          {staffQuery.isError && (
            <div className="mt-4">
              <ErrorState error={staffQuery.error} onRetry={() => staffQuery.refetch()} />
            </div>
          )}
          {staffQuery.data && (
            <div className="mt-4 overflow-x-auto rounded-lg border border-[var(--bo-divider)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--bo-canvas)] text-left text-xs font-medium text-[var(--bo-text-muted)]">
                  <tr>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Email</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Status</th>
                    {isOwner && <th className="px-4 py-3"></th>}
                  </tr>
                </thead>
                <tbody>
                  {staffQuery.data.map((s) => (
                    <tr key={s.id} className="h-14 border-t border-[var(--bo-divider)]">
                      <td className="px-4 py-3 font-medium text-[var(--bo-text)]">{s.full_name}</td>
                      <td className="px-4 py-3 text-[var(--bo-text-muted)]">{s.email}</td>
                      <td className="px-4 py-3 text-[var(--bo-text)]">{ROLE_LABELS[s.role]}</td>
                      <td className="px-4 py-3">
                        <StatusBadge active={s.is_active} activeLabel="Active" inactiveLabel="Deactivated" />
                      </td>
                      {isOwner && (
                        <td className="px-4 py-3 text-right">
                          {s.id !== admin.id && (
                            <button
                              disabled={updateStaff.isPending}
                              onClick={() => handleToggleActive(s.id, s.full_name, !s.is_active)}
                              className="h-9 rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm font-medium text-[var(--bo-text-secondary)] hover:bg-[var(--bo-surface-hover)]"
                            >
                              {s.is_active ? "Deactivate" : "Reactivate"}
                            </button>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {isOwner && (
          <div className="rounded-[14px] border border-[var(--bo-border)] bg-[var(--bo-surface)] p-5 shadow-[var(--bo-shadow-card)]">
            <h2 className="text-[17px] font-medium text-[var(--bo-text)]">Invite staff</h2>
            <form onSubmit={handleSubmit(onInvite)} className="mt-4 grid gap-4 sm:grid-cols-3">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" {...register("email")} />
                {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
              </div>
              <div>
                <Label htmlFor="full_name">Name (optional)</Label>
                <Input id="full_name" {...register("full_name")} />
              </div>
              <div>
                <Label htmlFor="role">Role</Label>
                <select
                  id="role"
                  {...register("role")}
                  className="h-10 w-full rounded-md border border-[var(--bo-border)] bg-[var(--bo-surface)] px-3 text-sm text-[var(--bo-text)]"
                >
                  <option value="support">Support</option>
                  <option value="admin">Admin</option>
                  <option value="owner">Owner</option>
                </select>
              </div>
              <div className="sm:col-span-3">
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Sending invite..." : "Send invite"}
                </Button>
              </div>
            </form>
            {createdLink && (
              <p className="mt-3 rounded-md bg-[var(--bo-primary-soft)] p-3 text-xs text-[var(--bo-text)]">
                One-time link (shown once -- send it to the person): <br />
                <span className="break-all font-medium">{createdLink}</span>
              </p>
            )}

            <h3 className="mt-6 text-sm font-medium text-[var(--bo-text)]">Pending invitations</h3>
            {invitationsQuery.data && invitationsQuery.data.length === 0 && (
              <div className="mt-2">
                <EmptyState title="No pending invitations" />
              </div>
            )}
            {invitationsQuery.data && invitationsQuery.data.length > 0 && (
              <ul className="mt-2 divide-y divide-[var(--bo-divider)]">
                {invitationsQuery.data.map((inv) => (
                  <li key={inv.id} className="flex items-center justify-between py-2 text-sm">
                    <span>
                      {inv.email} &middot; {ROLE_LABELS[inv.role]}
                      {inv.expired && <span className="ml-2 text-[var(--bo-danger)]">expired</span>}
                    </span>
                    <button
                      onClick={() => handleRevoke(inv.id, inv.email)}
                      className="text-xs font-medium text-[var(--bo-text-muted)] hover:text-[var(--bo-danger)]"
                    >
                      Revoke
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </PlatformShell>
  );
}
