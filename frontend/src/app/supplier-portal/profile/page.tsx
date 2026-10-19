"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { SupplierShell } from "@/components/supplier-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/supplier-api";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import {
  useChangeMemberRole,
  useInviteSupplierTeamMember,
  useReinstateMember,
  useRevokeMember,
  useSuspendMember,
  useSupplierDocuments,
  useSupplierPortalProfile,
  useSupplierTeamInvitations,
  useSupplierTeamMembers,
  useUpdateSupplierPortalProfile,
  useUploadSupplierPortalDocument,
} from "@/lib/use-supplier-portal";
import type { SupplierMembershipRole } from "@/lib/supplier-portal-types";

const STATUS_CLASSES: Record<string, string> = {
  active: "bg-green-50 text-green-700",
  suspended: "bg-amber-50 text-amber-700",
  revoked: "bg-red-50 text-red-700",
};

export default function SupplierProfilePage() {
  const { refreshToken, activeSupplierId, activeMembership, isLoading: authLoading } = useSupplierAuth();
  const router = useRouter();
  const { toast, confirm } = useFeedback();
  const canManage = activeMembership?.role === "owner" || activeMembership?.role === "admin";

  const profileQuery = useSupplierPortalProfile();
  const updateProfile = useUpdateSupplierPortalProfile();
  const documentsQuery = useSupplierDocuments();
  const uploadDocument = useUploadSupplierPortalDocument();
  const membersQuery = useSupplierTeamMembers();
  const invitationsQuery = useSupplierTeamInvitations();
  const inviteMember = useInviteSupplierTeamMember();
  const suspendMember = useSuspendMember();
  const revokeMember = useRevokeMember();
  const reinstateMember = useReinstateMember();
  const changeRole = useChangeMemberRole();

  const [phone, setPhone] = useState("");
  const [website, setWebsite] = useState("");
  const [address, setAddress] = useState("");
  const [notes, setNotes] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<SupplierMembershipRole>("staff");
  const [docTitle, setDocTitle] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!refreshToken) router.replace("/supplier-portal/login");
    else if (!activeSupplierId) router.replace("/supplier-portal/select-supplier");
  }, [authLoading, refreshToken, activeSupplierId, router]);

  useEffect(() => {
    if (profileQuery.data && !hydrated) {
      setPhone(profileQuery.data.phone ?? "");
      setWebsite(profileQuery.data.website ?? "");
      setAddress(profileQuery.data.address ?? "");
      setNotes(profileQuery.data.notes ?? "");
      setHydrated(true);
    }
  }, [profileQuery.data, hydrated]);

  if (authLoading || !refreshToken || !activeSupplierId) return null;

  async function handleSaveProfile() {
    try {
      await updateProfile.mutateAsync({ phone, website, address, notes });
      toast("Profile updated.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleUploadDocument() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    try {
      await uploadDocument.mutateAsync({ file, title: docTitle || file.name });
      setDocTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      toast("Document uploaded.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Upload failed.", "error");
    }
  }

  async function handleInvite() {
    try {
      await inviteMember.mutateAsync({ email: inviteEmail, role: inviteRole });
      setInviteEmail("");
      toast("Invitation sent.", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleSuspend(membershipId: string, name: string) {
    const ok = await confirm({ title: `Suspend ${name}?`, body: "They'll lose access immediately until reinstated.", confirmLabel: "Suspend", danger: true });
    if (!ok) return;
    try {
      await suspendMember.mutateAsync(membershipId);
      toast(`${name} suspended.`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  async function handleRevoke(membershipId: string, name: string) {
    const ok = await confirm({ title: `Revoke ${name}'s access?`, body: "This can't be undone -- they'd need a fresh invitation.", confirmLabel: "Revoke", danger: true });
    if (!ok) return;
    try {
      await revokeMember.mutateAsync(membershipId);
      toast(`${name}'s access revoked.`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  const profile = profileQuery.data;

  return (
    <SupplierShell breadcrumb="Profile">
      <div className="max-w-3xl space-y-5">
        {profileQuery.isError && <ErrorState error={profileQuery.error} onRetry={() => profileQuery.refetch()} />}
        {profileQuery.isLoading && <TableSkeleton rows={4} />}
        {profile && (
          <Card className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h1 className="text-lg font-semibold text-gray-900">{profile.name}</h1>
                {profile.legal_name && <p className="text-sm text-gray-500">{profile.legal_name}</p>}
              </div>
              <span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-medium capitalize text-teal-700">{profile.verification_status}</span>
            </div>
            <p className="text-xs text-gray-400">
              Business name, legal name and verification status are managed by BuildOS staff and can't be changed here.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} disabled={!canManage} />
              </div>
              <div>
                <Label htmlFor="website">Website</Label>
                <Input id="website" value={website} onChange={(e) => setWebsite(e.target.value)} disabled={!canManage} />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="address">Address</Label>
                <Input id="address" value={address} onChange={(e) => setAddress(e.target.value)} disabled={!canManage} />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="notes">Business description</Label>
                <textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={!canManage}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50"
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {profile.categories.map((c) => (
                <span key={c} className="rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-700">{c}</span>
              ))}
            </div>
            {canManage && (
              <Button onClick={handleSaveProfile} disabled={updateProfile.isPending}>
                {updateProfile.isPending ? "Saving..." : "Save changes"}
              </Button>
            )}
          </Card>
        )}

        <Card className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-900">Verification documents</h2>
          {documentsQuery.isLoading && <TableSkeleton rows={2} />}
          {documentsQuery.data && documentsQuery.data.length === 0 && <EmptyState title="No documents uploaded yet" />}
          <ul className="space-y-2">
            {documentsQuery.data?.map((d) => (
              <li key={d.id} className="flex items-center justify-between rounded-md border border-gray-200 px-3 py-2 text-sm">
                <span className="text-gray-900">{d.title}</span>
                <span className="text-xs text-gray-500">{(d.size_bytes / 1024).toFixed(0)} KB</span>
              </li>
            ))}
          </ul>
          {canManage && (
            <div className="flex flex-wrap items-end gap-2 border-t border-gray-100 pt-3">
              <Input placeholder="Document title" value={docTitle} onChange={(e) => setDocTitle(e.target.value)} className="w-48" />
              <input ref={fileInputRef} type="file" className="text-sm" />
              <Button onClick={handleUploadDocument} disabled={uploadDocument.isPending}>
                {uploadDocument.isPending ? "Uploading..." : "Upload"}
              </Button>
            </div>
          )}
        </Card>

        <Card className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-900">Team members</h2>
          {membersQuery.isLoading && <TableSkeleton rows={2} />}
          <ul className="space-y-2">
            {membersQuery.data?.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm">
                <div>
                  <p className="font-medium text-gray-900">{m.user_full_name}</p>
                  <p className="text-xs text-gray-500">{m.user_email}</p>
                </div>
                <div className="flex items-center gap-2">
                  {canManage ? (
                    <select
                      value={m.role}
                      onChange={(e) => changeRole.mutate({ membershipId: m.id, role: e.target.value as SupplierMembershipRole })}
                      className="h-8 rounded-md border border-gray-300 px-2 text-xs capitalize"
                    >
                      <option value="owner">Owner</option>
                      <option value="admin">Admin</option>
                      <option value="staff">Staff</option>
                    </select>
                  ) : (
                    <span className="text-xs capitalize text-gray-500">{m.role}</span>
                  )}
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_CLASSES[m.status]}`}>{m.status}</span>
                  {canManage && m.status === "active" && (
                    <button onClick={() => handleSuspend(m.id, m.user_full_name)} className="text-xs font-medium text-amber-600 hover:underline">Suspend</button>
                  )}
                  {canManage && m.status === "suspended" && (
                    <button onClick={() => reinstateMember.mutate(m.id)} className="text-xs font-medium text-green-600 hover:underline">Reinstate</button>
                  )}
                  {canManage && m.status !== "revoked" && (
                    <button onClick={() => handleRevoke(m.id, m.user_full_name)} className="text-xs font-medium text-red-600 hover:underline">Revoke</button>
                  )}
                </div>
              </li>
            ))}
          </ul>

          {canManage && (
            <div className="flex flex-wrap items-end gap-2 border-t border-gray-100 pt-3">
              <Input placeholder="teammate@company.com" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="w-56" />
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as SupplierMembershipRole)} className="h-10 rounded-md border border-gray-300 px-2 text-sm">
                <option value="staff">Staff</option>
                <option value="admin">Admin</option>
                <option value="owner">Owner</option>
              </select>
              <Button onClick={handleInvite} disabled={!inviteEmail || inviteMember.isPending}>
                {inviteMember.isPending ? "Inviting..." : "Invite"}
              </Button>
            </div>
          )}

          {invitationsQuery.data && invitationsQuery.data.length > 0 && (
            <div className="border-t border-gray-100 pt-3">
              <p className="mb-2 text-xs font-medium text-gray-500">Pending invitations</p>
              <ul className="space-y-1">
                {invitationsQuery.data.map((inv) => (
                  <li key={inv.id} className="flex justify-between text-sm text-gray-700">
                    <span>{inv.email} ({inv.role})</span>
                    <span className={inv.expired ? "text-red-500" : "text-gray-400"}>{inv.expired ? "expired" : "pending"}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      </div>
    </SupplierShell>
  );
}
