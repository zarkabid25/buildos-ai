"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState, Skeleton } from "@/components/ui/states";
import { ApiError } from "@/lib/supplier-api";
import { useSupplierAcceptInvite, useSupplierInvitationInfo } from "@/lib/use-supplier-portal";
import type { SupplierInvitationInfo } from "@/lib/supplier-portal-types";

function AcceptInviteForm() {
  const params = useSearchParams();
  const router = useRouter();
  const { toast } = useFeedback();
  const token = params.get("token") ?? "";
  const { data, isLoading, isError, error } = useSupplierInvitationInfo(token);
  const info = data as SupplierInvitationInfo | undefined;
  const acceptInvite = useSupplierAcceptInvite();
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await acceptInvite.mutateAsync({ token, full_name: fullName, password });
      toast("Account created. Sign in to continue.", "success");
      router.push("/supplier-portal/login");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Something went wrong.", "error");
    }
  }

  if (isLoading) return <Skeleton className="h-48 w-full max-w-sm" />;
  if (isError || !info) return <ErrorState error={error} />;

  return (
    <Card className="w-full max-w-sm space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Join {info.marketplace_supplier_name}</h1>
        <p className="mt-1 text-sm text-gray-500">
          You've been invited as {info.email} ({info.role}).
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="full_name">Your name</Label>
          <Input id="full_name" required value={fullName} onChange={(e) => setFullName(e.target.value)} defaultValue={info.full_name ?? ""} />
        </div>
        <div>
          <Label htmlFor="password">Choose a password</Label>
          <Input id="password" type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <Button type="submit" className="h-11 w-full text-base" disabled={acceptInvite.isPending}>
          {acceptInvite.isPending ? "Creating account..." : "Create account"}
        </Button>
      </form>
    </Card>
  );
}

export default function SupplierAcceptInvitePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Suspense fallback={<Skeleton className="h-48 w-full max-w-sm" />}>
        <AcceptInviteForm />
      </Suspense>
    </div>
  );
}
