"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { AuthResponse, UserRole } from "@/lib/auth-types";
import { acceptInviteSchema, type AcceptInviteInput } from "@/lib/schemas";
import { ROLE_LABELS } from "@/lib/settings-types";

interface InviteInfo {
  company_name: string;
  email: string;
  full_name: string | null;
  role: UserRole;
}

export default function AcceptInvitePage() {
  const { setSession, user, logout } = useAuth();
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [info, setInfo] = useState<InviteInfo | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AcceptInviteInput>({ resolver: zodResolver(acceptInviteSchema) });

  // Read the token from the link (not useSearchParams, which would need a Suspense boundary).
  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("token");
    if (!t) {
      setLinkError("This link is missing its invitation code. Ask whoever invited you to send it again.");
      return;
    }
    setToken(t);
    api
      .get<InviteInfo>(`/auth/invitations/${encodeURIComponent(t)}`)
      .then((i) => {
        setInfo(i);
        reset({ full_name: i.full_name ?? "", password: "", confirm: "" });
      })
      .catch((err) =>
        setLinkError(err instanceof ApiError ? err.message : "Couldn't check this invitation. Try again in a moment.")
      );
  }, [reset]);

  async function onSubmit(values: AcceptInviteInput) {
    if (!token) return;
    setServerError(null);
    try {
      const auth = await api.post<AuthResponse>("/auth/accept-invite", {
        token,
        full_name: values.full_name,
        password: values.password,
      });
      setSession(auth);
      router.push("/dashboard");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold text-ink">BuildOS AI</h1>

        {linkError && (
          <>
            <p className="mb-4 text-sm text-danger">{linkError}</p>
            <Link href="/login" className="text-sm font-medium text-primary">
              Go to sign in
            </Link>
          </>
        )}

        {!linkError && !info && (
          <div className="space-y-2 py-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        )}

        {info && (
          <>
            <p className="mb-6 text-sm text-muted">
              You&apos;ve been invited to join <span className="font-medium text-ink">{info.company_name}</span> as{" "}
              <span className="font-medium text-ink">{ROLE_LABELS[info.role]}</span>. Set up your account to continue.
            </p>
            {user && (
              <p className="mb-4 rounded-md bg-amber-50 p-2 text-xs text-ink">
                You&apos;re signed in as {user.email}. Accepting will sign you in as {info.email} instead.{" "}
                <button className="text-primary underline" onClick={logout}>
                  Sign out first
                </button>
              </p>
            )}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" value={info.email} disabled readOnly />
              </div>
              <div>
                <Label htmlFor="full_name">Your name</Label>
                <Input id="full_name" autoComplete="name" {...register("full_name")} />
                {errors.full_name && <p className="mt-1 text-xs text-danger">{errors.full_name.message}</p>}
              </div>
              <div>
                <Label htmlFor="password">Choose a password</Label>
                <Input id="password" type="password" autoComplete="new-password" {...register("password")} />
                {errors.password && <p className="mt-1 text-xs text-danger">{errors.password.message}</p>}
              </div>
              <div>
                <Label htmlFor="confirm">Repeat password</Label>
                <Input id="confirm" type="password" autoComplete="new-password" {...register("confirm")} />
                {errors.confirm && <p className="mt-1 text-xs text-danger">{errors.confirm.message}</p>}
              </div>
              {serverError && <p className="text-sm text-danger">{serverError}</p>}
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Setting up..." : "Join and sign in"}
              </Button>
            </form>
          </>
        )}
      </Card>
    </div>
  );
}
