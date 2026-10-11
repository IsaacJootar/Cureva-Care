"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { roleLanding } from "@/lib/nav";
import { useIsMobile } from "@/lib/useIsMobile";
import type { Role } from "@/lib/types";
import { BottomNav } from "./BottomNav";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

// Authenticated page frame + route guard. Redirects to /login when not signed
// in, and enforces role access server-side-consistent redirects on the client
// (the API is the real gate; this just avoids showing a screen a role can't use).
export function AppShell({
  title,
  subtitle,
  chips,
  action,
  allowedRoles,
  children,
}: {
  title: string;
  subtitle?: string;
  chips?: ReactNode;
  action?: ReactNode;
  allowedRoles?: Role[];
  children: ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
    } else if (allowedRoles && !allowedRoles.includes(user.role)) {
      router.replace(roleLanding(user.role));
    }
  }, [loading, user, allowedRoles, router]);

  if (loading || !user || (allowedRoles && !allowedRoles.includes(user.role))) {
    return (
      <main style={{ minHeight: "100dvh", display: "grid", placeItems: "center" }}>
        <span style={{ color: "var(--cv-text-muted)", fontSize: 12.5 }}>Loading…</span>
      </main>
    );
  }

  if (isMobile) {
    return (
      <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh" }}>
        <TopBar title={title} subtitle={subtitle} chips={chips} action={action} />
        <main style={{ padding: 16, flex: 1, paddingBottom: 80, maxWidth: "100vw", overflowX: "hidden" }}>
          {children}
        </main>
        <BottomNav user={user} />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", minHeight: "100dvh" }}>
      <Sidebar user={user} />
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <TopBar title={title} subtitle={subtitle} chips={chips} action={action} />
        <main style={{ padding: 24, flex: 1 }}>{children}</main>
      </div>
    </div>
  );
}
