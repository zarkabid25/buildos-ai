"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { AuthResponse } from "@/lib/auth-types";
import { registerSchema, type RegisterInput } from "@/lib/schemas";

export default function RegisterPage() {
  const { setSession } = useAuth();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput>({ resolver: zodResolver(registerSchema) });

  async function onSubmit(values: RegisterInput) {
    setServerError(null);
    try {
      const auth = await api.post<AuthResponse>("/auth/register", values);
      setSession(auth);
      router.push("/dashboard");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-10">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold text-ink">Create your company</h1>
        <p className="mb-6 text-sm text-muted">Set up BuildOS AI for your construction business.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="company_name">Company name</Label>
            <Input id="company_name" {...register("company_name")} />
            {errors.company_name && (
              <p className="mt-1 text-xs text-danger">{errors.company_name.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="company_code">Company code</Label>
            <Input id="company_code" placeholder="e.g. ACME" {...register("company_code")} />
            {errors.company_code && (
              <p className="mt-1 text-xs text-danger">{errors.company_code.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="full_name">Your full name</Label>
            <Input id="full_name" {...register("full_name")} />
            {errors.full_name && (
              <p className="mt-1 text-xs text-danger">{errors.full_name.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" {...register("email")} />
            {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" {...register("password")} />
            {errors.password && (
              <p className="mt-1 text-xs text-danger">{errors.password.message}</p>
            )}
          </div>
          {serverError && <p className="text-sm text-danger">{serverError}</p>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
