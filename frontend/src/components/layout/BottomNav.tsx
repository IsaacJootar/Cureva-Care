"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { navForUser, type NavLink } from "@/lib/nav";
import type { CurrentUser } from "@/lib/types";
import { XIcon } from "../icons";

// Mobile bottom tab bar (cureva-docs/09 "Mobile bottom-sheet overflow"). Up to
// four fixed tabs; when a role has more, the fourth is "More" opening a sheet
// with the overflow. A Data officer's two links show as a simple two-item bar.
function isActive(pathname: string, href: string): boolean {
  const base = href.split("?")[0];
  if (base === "/overview") return pathname === "/overview";
  return pathname === base || pathname.startsWith(base + "/");
}

export function BottomNav({ user }: { user: CurrentUser }) {
  const pathname = usePathname();
  const [sheetOpen, setSheetOpen] = useState(false);
  const nav = navForUser(user);
  const links: NavLink[] = nav.groups.flatMap((g) => g.links);

  const fitsAll = links.length <= 4;
  const tabs = fitsAll ? links : links.slice(0, 3);
  const overflow = fitsAll ? [] : links.slice(3);

  return (
    <>
      <nav
        style={{
          position: "fixed",
          left: 0,
          right: 0,
          bottom: 0,
          height: 64,
          background: "var(--cv-sidebar-bg)",
          display: "flex",
          alignItems: "stretch",
          zIndex: 60,
          borderTop: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        {tabs.map((l) => (
          <Tab key={l.href} href={l.href} label={l.label} icon={l.icon} active={isActive(pathname, l.href)} />
        ))}
        {overflow.length > 0 && (
          <button
            onClick={() => setSheetOpen(true)}
            style={{ flex: 1, background: "none", border: "none", color: "var(--cv-text-on-dark-secondary)", cursor: "pointer", fontSize: 10.5, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 3 }}
          >
            <span style={{ fontSize: 16 }}>⋯</span>
            More
          </button>
        )}
      </nav>

      {sheetOpen && (
        <div onMouseDown={(e) => e.target === e.currentTarget && setSheetOpen(false)} style={{ position: "fixed", inset: 0, background: "rgba(11,11,11,0.42)", zIndex: 70 }}>
          <div style={{ position: "fixed", left: 0, right: 0, bottom: 64, background: "var(--cv-card-bg)", borderTopLeftRadius: 16, borderTopRightRadius: 16, padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>More</span>
              <button onClick={() => setSheetOpen(false)} aria-label="Close" style={{ background: "none", border: "none", color: "var(--cv-text-muted)", cursor: "pointer" }}>
                <XIcon size={16} />
              </button>
            </div>
            {overflow.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setSheetOpen(false)}
                style={{ display: "flex", alignItems: "center", gap: 11, padding: "11px 6px", textDecoration: "none", color: "var(--cv-text-primary)", fontSize: 13, borderBottom: "1px solid var(--cv-hairline)" }}
              >
                <span style={{ color: "var(--cv-text-muted)" }}>{l.icon}</span>
                {l.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function Tab({ href, label, icon, active }: { href: string; label: string; icon: React.ReactNode; active: boolean }) {
  return (
    <Link
      href={href}
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 3,
        textDecoration: "none",
        fontSize: 10.5,
        color: active ? "var(--cv-text-on-dark)" : "var(--cv-text-on-dark-muted)",
        fontWeight: active ? 600 : 400,
      }}
    >
      <span style={{ color: active ? "#9cc0ff" : "var(--cv-text-on-dark-muted)" }}>{icon}</span>
      {label}
    </Link>
  );
}
