"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { useFeedback } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/supplier-api";
import { useSupplierAuth } from "@/lib/supplier-auth-context";
import { useSupplierLogin } from "@/lib/use-supplier-portal";

export default function SupplierLoginPage() {
  const router = useRouter();
  const { toast } = useFeedback();
  const { setSession } = useSupplierAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useSupplierLogin();
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const auth = await login.mutateAsync({ email, password });
      setSession(auth);
      if (auth.active_supplier_id) {
        router.push("/supplier-portal");
      } else {
        router.push("/supplier-portal/select-supplier");
      }
      toast(`Welcome back, ${auth.user.full_name}.`, "success");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-sm space-y-5">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Supplier Portal</h1>
          <p className="mt-1 text-sm text-gray-500">Sign in to manage your catalog, RFQs and orders.</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="h-11 w-full text-base" disabled={login.isPending}>
            {login.isPending ? "Signing in..." : "Sign in"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
