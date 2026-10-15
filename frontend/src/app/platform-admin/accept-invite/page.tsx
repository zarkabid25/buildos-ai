"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/states";
import { ApiError, platformApi } from "@/lib/platform-api";
import { usePlatformAuth } from "@/lib/platform-auth-context";
import type { PlatformAuthResponse, PlatformInvitationInfo } from "@/lib/platform-types";
import { acceptInviteSchema, type AcceptInviteInput } from "@/lib/schemas";

const ROLE_LABELS = { owner: "Owner", admin: "Admin", support: "Support" };

export default function PlatformAcceptInvitePage() {
  const { setSession } = usePlatformAuth();
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [info, setInfo] = useState<PlatformInvitationInfo | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AcceptInviteInput>({ resolver: zodResolver(acceptInviteSchema) });

  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("token");
    if (!t) {
      setLinkError("This link is missing its invitation code. Ask whoever invited you to send it again.");
      return;
    }
    setToken(t);
    platformApi
      .get<PlatformInvitationInfo>(`/platform/auth/invitations/${encodeURIComponent(t)}`)
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
      const auth = await platformApi.post<PlatformAuthResponse>("/platform/auth/accept-invite", {
        token,
        full_name: values.full_name,
        password: values.password,
      });
      setSession(auth);
      router.push("/platform-admin/dashboard");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold text-ink">BuildOS Platform</h1>

        {linkError && <p className="mb-4 text-sm text-danger">{linkError}</p>}

        {!linkError && !info && (
          <div className="space-y-2 py-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        )}

        {info && (
          <>
            <p className="mb-6 text-sm text-muted">
              You&apos;ve been invited to join BuildOS AI&apos;s platform staff as{" "}
              <span className="font-medium text-ink">{ROLE_LABELS[info.role]}</span>. Set up your account to
              continue.
            </p>
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
