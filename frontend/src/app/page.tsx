"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { roleLanding } from "@/lib/nav";

// Role-aware entry: send signed-in users to their landing, everyone else to login.
export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? roleLanding(user.role) : "/login");
  }, [loading, user, router]);

  return (
    <main style={{ minHeight: "100dvh", display: "grid", placeItems: "center" }}>
      <span style={{ color: "var(--cv-text-muted)", fontSize: 12.5 }}>Loading…</span>
    </main>
  );
}
