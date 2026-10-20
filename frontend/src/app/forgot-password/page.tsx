"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/auth/forgot-password", { email });
      // Always shows the same confirmation whether or not the email has an
      // account -- never reveals which emails are registered.
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold text-ink">Reset your password</h1>
        {done ? (
          <p className="mt-4 text-sm text-muted">
            If an account exists for that email, we've sent a link to reset your password.
          </p>
        ) : (
          <>
            <p className="mb-6 text-sm text-muted">Enter your email and we'll send you a reset link.</p>
            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              {error && <p className="text-sm text-danger">{error}</p>}
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Sending..." : "Send reset link"}
              </Button>
            </form>
          </>
        )}
        <p className="mt-6 text-center text-sm text-muted">
          <Link href="/login" className="font-medium text-primary">
            Back to sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
