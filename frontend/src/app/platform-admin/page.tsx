"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { usePlatformAuth } from "@/lib/platform-auth-context";

export default function PlatformAdminIndexPage() {
  const { admin, isLoading } = usePlatformAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    router.replace(admin ? "/platform-admin/dashboard" : "/platform-admin/login");
  }, [isLoading, admin, router]);

  return null;
}
