"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { QueryView } from "@/components/ui/states";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { UserRole } from "@/lib/auth-types";
import { useAiStatus } from "@/lib/use-ai";
import { inviteSchema } from "@/lib/schemas";
import { ROLE_LABELS, type Company } from "@/lib/settings-types";
import {
  useAuditLog,
  useChangePassword,
  useCompany,
  useCreateInvitation,
  useInvitations,
  useRevokeInvitation,
  useUpdateCompany,
  useUpdateMe,
  useUpdateUser,
  useUsers,
} from "@/lib/use-settings";

const ADMIN_ROLES: UserRole[] = ["super_admin", "company_admin"];

function errorText(err: unknown, fallback: string) {
  // 422s carry a list of field errors, not a sentence; show the fallback for those.
  return err instanceof ApiError && typeof err.message === "string" && err.status !== 422 ? err.message : fallback;
}

export default function SettingsPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) return null;
  const isAdmin = ADMIN_ROLES.includes(user.role);

  return (
    <AppShell>
      <div className="max-w-4xl space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Settings</h1>
          <p className="text-muted">Your profile, your company, and who can do what.</p>
        </div>
        <ProfileSection />
        <CompanySection canEdit={isAdmin} />
        <AiSection />
        {isAdmin && <TeamSection currentUserId={user.id} currentRole={user.role} />}
        {isAdmin && <InvitationsSection currentRole={user.role} />}
        {isAdmin && <ActivitySection />}
      </div>
    </AppShell>
  );
}

function ProfileSection() {
  const { user } = useAuth();
  const updateMe = useUpdateMe();
  const changePassword = useChangePassword();
  const [name, setName] = useState(user?.full_name ?? "");
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [pwMessage, setPwMessage] = useState<{ ok: boolean; text: string } | null>(null);

  async function handlePassword() {
    if (pw.new_password.length < 8) {
      setPwMessage({ ok: false, text: "The new password must be at least 8 characters." });
      return;
    }
    try {
      await changePassword.mutateAsync(pw);
      setPw({ current_password: "", new_password: "" });
      setPwMessage({ ok: true, text: "Password changed." });
    } catch (err) {
      setPwMessage({ ok: false, text: errorText(err, "Could not change the password.") });
    }
  }

  return (
    <Card className="space-y-4">
      <h2 className="text-base font-semibold text-ink">Profile</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="sm:col-span-2">
          <Label htmlFor="full_name">Full name</Label>
          <Input id="full_name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex items-end">
          <Button
            onClick={() => updateMe.mutate({ full_name: name })}
            disabled={!name.trim() || updateMe.isPending || name === user?.full_name}
          >
            {updateMe.isPending ? "Saving..." : "Save name"}
          </Button>
        </div>
      </div>
      <p className="text-sm text-muted">
        {user?.email} · {user ? ROLE_LABELS[user.role] : ""}
      </p>

      <div className="border-t border-border pt-4">
        <h3 className="mb-2 text-sm font-semibold text-ink">Change password</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <Label htmlFor="current_password">Current password</Label>
            <Input
              id="current_password"
              type="password"
              autoComplete="current-password"
              value={pw.current_password}
              onChange={(e) => setPw({ ...pw, current_password: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="new_password">New password</Label>
            <Input
              id="new_password"
              type="password"
              autoComplete="new-password"
              value={pw.new_password}
              onChange={(e) => setPw({ ...pw, new_password: e.target.value })}
            />
          </div>
          <div className="flex items-end">
            <Button
              variant="secondary"
              onClick={handlePassword}
              disabled={!pw.current_password || !pw.new_password || changePassword.isPending}
            >
              Change password
            </Button>
          </div>
        </div>
        {pwMessage && (
          <p className={`mt-2 text-sm ${pwMessage.ok ? "text-success" : "text-danger"}`}>{pwMessage.text}</p>
        )}
      </div>
    </Card>
  );
}

function CompanySection({ canEdit }: { canEdit: boolean }) {
  const { data: company } = useCompany();
  if (!company) return null;
  return <CompanyForm key={company.id} company={company} canEdit={canEdit} />;
}

function CompanyForm({ company, canEdit }: { company: Company; canEdit: boolean }) {
  const updateCompany = useUpdateCompany();
  const [form, setForm] = useState({
    name: company.name,
    currency: company.currency,
    unit_system: company.unit_system,
    address: company.address ?? "",
    phone: company.phone ?? "",
    email: company.email ?? "",
  });
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  async function handleSave() {
    const currency = form.currency.trim().toUpperCase();
    if (!/^[A-Z]{3}$/.test(currency)) {
      setMessage({ ok: false, text: "Currency must be a 3-letter code such as PKR, USD or AED." });
      return;
    }
    if (form.name.trim().length < 2) {
      setMessage({ ok: false, text: "Company name must be at least 2 characters." });
      return;
    }
    try {
      await updateCompany.mutateAsync({
        name: form.name.trim(),
        currency,
        unit_system: form.unit_system,
        address: form.address.trim() || null,
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
      });
      setMessage({ ok: true, text: "Company settings saved." });
    } catch (err) {
      setMessage({ ok: false, text: errorText(err, "Could not save. Check the email address and try again.") });
    }
  }

  return (
    <Card className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h2 className="text-base font-semibold text-ink">Company</h2>
        <span className="text-xs text-muted">Code {company.code}</span>
      </div>
      {!canEdit && <p className="text-sm text-muted">Only company admins can change these settings.</p>}
      <fieldset disabled={!canEdit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="company_name">Name</Label>
          <Input id="company_name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="company_email">Email</Label>
          <Input id="company_email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="company_phone">Phone</Label>
          <Input id="company_phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="company_address">Address</Label>
          <Input
            id="company_address"
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="company_currency">Currency (3-letter code)</Label>
          <Input
            id="company_currency"
            maxLength={3}
            value={form.currency}
            onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })}
          />
        </div>
        <div>
          <Label htmlFor="company_units">Unit system</Label>
          <select
            id="company_units"
            className="h-9 w-full rounded-md border border-border bg-surface px-2 text-sm"
            value={form.unit_system}
            onChange={(e) => setForm({ ...form, unit_system: e.target.value as Company["unit_system"] })}
          >
            <option value="metric">Metric</option>
            <option value="imperial">Imperial</option>
          </select>
        </div>
      </fieldset>
      <p className="text-xs text-muted">
        The currency is used for every amount shown in the app. It&apos;s a display label only: amounts
        aren&apos;t converted. The unit system is saved for reference, but material units are still set
        per material and nothing is converted automatically.
      </p>
      {canEdit && (
        <div className="flex items-center gap-3">
          <Button onClick={handleSave} disabled={updateCompany.isPending}>
            {updateCompany.isPending ? "Saving..." : "Save company settings"}
          </Button>
          {message && <span className={`text-sm ${message.ok ? "text-success" : "text-danger"}`}>{message.text}</span>}
        </div>
      )}
    </Card>
  );
}

function AiSection() {
  const { data: status } = useAiStatus();
  if (!status) return null;
  return (
    <Card className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="text-base font-semibold text-ink">AI assistant</h2>
        <span className={`text-sm ${status.configured ? "text-success" : "text-muted"}`}>
          {status.configured ? "Connected" : "Not switched on"}
        </span>
      </div>
      <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted">Provider</dt>
          <dd className="capitalize text-ink">{status.provider}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted">Model</dt>
          <dd className="text-ink">{status.model}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted">Tool steps per answer</dt>
          <dd className="text-ink">up to {status.max_tool_iterations}</dd>
        </div>
      </dl>
      <p className="text-xs text-muted">
        These are set on the server (<code>LLM_API_KEY</code>, <code>LLM_MODEL</code> and related
        environment variables), not here, so the API key is never stored in or shown by the app.
        {status.configured
          ? ""
          : " Until a key is set, the chat is disabled; rules-based insights still work."}{" "}
        The assistant only drafts changes such as material requests; a person always approves them.
      </p>
    </Card>
  );
}

function TeamSection({ currentUserId, currentRole }: { currentUserId: string; currentRole: UserRole }) {
  const { data: users, isLoading } = useUsers(true);
  const updateUser = useUpdateUser();
  const { confirm } = useFeedback();
  const [error, setError] = useState<string | null>(null);

  // Only a super admin can hand out (or take away) super admin.
  const assignable = (Object.keys(ROLE_LABELS) as UserRole[]).filter(
    (r) => r !== "super_admin" || currentRole === "super_admin"
  );

  async function change(id: string, input: { role?: UserRole; is_active?: boolean }) {
    setError(null);
    try {
      await updateUser.mutateAsync({ id, ...input });
    } catch (err) {
      setError(errorText(err, "Could not update that user."));
    }
  }

  return (
    <Card className="space-y-3">
      <h2 className="text-base font-semibold text-ink">Team and roles</h2>
      <p className="text-xs text-muted">
        A role decides what each person can do (for example, only admins and project managers approve
        purchase orders). You can&apos;t change your own role or deactivate yourself. Add people with an
        invitation below.
      </p>
      {error && <p className="text-sm text-danger">{error}</p>}
      {isLoading && <p className="text-sm text-muted">Loading users...</p>}
      {users && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Email</th>
                <th className="px-2 py-2">Role</th>
                <th className="px-2 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const locked =
                  u.id === currentUserId || (u.role === "super_admin" && currentRole !== "super_admin");
                return (
                  <tr key={u.id} className="border-b border-border last:border-0">
                    <td className="px-2 py-2 font-medium text-ink">
                      {u.full_name}
                      {u.id === currentUserId && <span className="ml-1 text-xs text-muted">(you)</span>}
                    </td>
                    <td className="px-2 py-2 text-muted">{u.email}</td>
                    <td className="px-2 py-2">
                      {locked ? (
                        ROLE_LABELS[u.role]
                      ) : (
                        <select
                          aria-label={`Role for ${u.full_name}`}
                          className="h-8 rounded-md border border-border bg-surface px-2 text-sm"
                          value={u.role}
                          disabled={updateUser.isPending}
                          onChange={(e) => change(u.id, { role: e.target.value as UserRole })}
                        >
                          {assignable.map((r) => (
                            <option key={r} value={r}>
                              {ROLE_LABELS[r]}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      {locked ? (
                        u.is_active ? "Active" : "Deactivated"
                      ) : (
                        <button
                          className={`text-xs ${u.is_active ? "text-muted hover:text-danger" : "text-primary"}`}
                          disabled={updateUser.isPending}
                          onClick={async () => {
                            const ok =
                              !u.is_active ||
                              (await confirm({
                                title: `Deactivate ${u.full_name}?`,
                                body: "They'll be signed out and can't log in until reactivated.",
                                confirmLabel: "Deactivate",
                                danger: true,
                              }));
                            if (ok) change(u.id, { is_active: !u.is_active });
                          }}
                        >
                          {u.is_active ? "Deactivate" : "Reactivate"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function ActivitySection() {
  const query = useAuditLog(true);
  return (
    <Card className="space-y-3">
      <h2 className="text-base font-semibold text-ink">Activity log</h2>
      <p className="text-xs text-muted">
        Approvals, money, permission changes and deletions, newest first. Entries can&apos;t be edited or removed.
      </p>
      <QueryView
        query={query}
        isEmpty={(entries) => entries.length === 0}
        empty={<p className="text-sm text-muted">Nothing recorded yet.</p>}
      >
        {(entries) => (
          <ul className="divide-y divide-border text-sm">
            {entries.map((e) => (
              <li key={e.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2">
                <span className="text-ink">{e.summary}</span>
                <span className="text-xs text-muted">
                  {e.actor_name ?? "Unknown user"} · {new Date(e.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </QueryView>
    </Card>
  );
}

function InvitationsSection({ currentRole }: { currentRole: UserRole }) {
  const invitations = useInvitations(true);
  const create = useCreateInvitation();
  const revoke = useRevokeInvitation();
  const { confirm, toast } = useFeedback();
  const [form, setForm] = useState({ email: "", full_name: "", role: "site_engineer" as UserRole });
  const [error, setError] = useState<string | null>(null);
  const [link, setLink] = useState<{ email: string; url: string } | null>(null);
  const roles = (Object.keys(ROLE_LABELS) as UserRole[]).filter((r) => r !== "super_admin" || currentRole === "super_admin");

  async function handleInvite() {
    setError(null);
    const parsed = inviteSchema.safeParse({ ...form, full_name: form.full_name || undefined });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Check the form");
      return;
    }
    try {
      const created = await create.mutateAsync(parsed.data);
      setLink({ email: created.email, url: `${window.location.origin}/accept-invite?token=${created.token}` });
      setForm({ email: "", full_name: "", role: form.role });
    } catch (err) {
      setError(errorText(err, "Could not create the invitation."));
    }
  }

  async function copy(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      toast("Invite link copied.", "success");
    } catch {
      toast("Couldn't copy automatically; select the link and copy it.", "info");
    }
  }

  return (
    <Card className="space-y-3">
      <h2 className="text-base font-semibold text-ink">Invite people</h2>
      <p className="text-xs text-muted">
        Creates a one-time link, valid for 7 days, that you send to the person yourself (e.g. by email or WhatsApp).
        They choose their own password. Inviting the same email again replaces the old link.
      </p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
        <Input aria-label="Invitee email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input aria-label="Invitee name (optional)" placeholder="Name (optional)" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <select
          aria-label="Invitee role"
          className="h-9 rounded-md border border-border bg-surface px-2 text-sm"
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
        >
          {roles.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABELS[r]}
            </option>
          ))}
        </select>
        <Button onClick={handleInvite} disabled={create.isPending || !form.email.trim()}>
          {create.isPending ? "Creating..." : "Create invite link"}
        </Button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {link && (
        <div className="space-y-1 rounded-md border border-success/40 bg-green-50/60 p-3">
          <p className="text-sm text-ink">
            Send this link to {link.email}. It&apos;s shown only once; if it&apos;s lost, invite them again.
          </p>
          <div className="flex gap-2">
            <Input aria-label="Invite link" readOnly value={link.url} onFocus={(e) => e.target.select()} />
            <Button variant="secondary" onClick={() => copy(link.url)}>
              Copy
            </Button>
          </div>
        </div>
      )}
      <QueryView
        query={invitations}
        isEmpty={(list) => list.length === 0}
        empty={<p className="text-sm text-muted">No pending invitations.</p>}
      >
        {(list) => (
          <ul className="divide-y divide-border text-sm">
            {list.map((inv) => (
              <li key={inv.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>
                  <span className="text-ink">{inv.full_name ? `${inv.full_name} · ` : ""}{inv.email}</span>
                  <span className="ml-2 text-xs text-muted">{ROLE_LABELS[inv.role]}</span>
                </span>
                <span className="flex items-center gap-3 text-xs">
                  {inv.expired ? (
                    <span className="text-danger">Expired</span>
                  ) : (
                    <span className="text-muted">Expires {new Date(inv.expires_at).toLocaleDateString()}</span>
                  )}
                  <button
                    className="text-muted hover:text-danger"
                    onClick={async () => {
                      const ok = await confirm({ title: `Revoke the invitation for ${inv.email}?`, body: "The link stops working.", confirmLabel: "Revoke", danger: true });
                      if (ok) revoke.mutate(inv.id);
                    }}
                  >
                    {inv.expired ? "Remove" : "Revoke"}
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </QueryView>
    </Card>
  );
}
