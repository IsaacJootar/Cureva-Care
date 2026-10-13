"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navForUser, type NavGroup } from "@/lib/nav";
import { CheckIcon } from "../icons";
import type { CurrentUser } from "@/lib/types";
import { AccountMenu } from "./AccountMenu";

function isActive(pathname: string, href: string): boolean {
  const base = href.split("?")[0];
  if (base === "/overview") return pathname === "/overview";
  return pathname === base || pathname.startsWith(base + "/");
}

export function Sidebar({ user }: { user: CurrentUser }) {
  const pathname = usePathname();
  const nav = navForUser(user);

  return (
    <aside
      style={{
        width: 240,
        flexShrink: 0,
        background: "var(--cv-sidebar-bg)",
        display: "flex",
        flexDirection: "column",
        padding: "18px 14px",
        gap: 6,
        minHeight: "100dvh",
        position: "sticky",
        top: 0,
      }}
    >
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 8px 14px" }}>
        <span
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: "var(--cv-accent-gradient)",
            boxShadow: "var(--cv-accent-glow)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
          }}
        >
          <CheckIcon size={16} />
        </span>
        <span className="cv-brand" style={{ color: "var(--cv-text-on-dark)", fontSize: 16 }}>
          Cureva Care
        </span>
      </div>

      {/* Facility context row (Facility lead only) */}
      {nav.contextRow && (
        <div style={{ padding: "8px 10px", marginBottom: 4 }}>
          <div style={{ color: "var(--cv-text-on-dark)", fontSize: 12.5, fontWeight: 600 }}>
            {nav.contextRow.title}
          </div>
          <div style={{ color: "var(--cv-text-on-dark-muted)", fontSize: 10.5, marginTop: 2 }}>
            {nav.contextRow.caption}
          </div>
        </div>
      )}

      {/* Nav groups */}
      <nav style={{ display: "flex", flexDirection: "column", gap: 14, flex: 1 }}>
        {nav.groups.map((group, i) => (
          <NavGroupBlock key={group.label ?? i} group={group} pathname={pathname} />
        ))}
      </nav>

      {/* User footer → full Account menu popover (Profile / Notifications / Sign out). */}
      <div style={{ marginTop: 6 }}>
        <AccountMenu user={user} />
      </div>
    </aside>
  );
}

function NavGroupBlock({ group, pathname }: { group: NavGroup; pathname: string }) {
  return (
    <div>
      {group.label && (
        <div
          style={{
            fontSize: 10,
            letterSpacing: "0.6px",
            textTransform: "uppercase",
            color: "var(--cv-text-on-dark-muted)",
            padding: "0 10px 8px",
            fontWeight: 600,
          }}
        >
          {group.label}
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {group.links.map((link) => {
          const active = isActive(pathname, link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 10px",
                borderRadius: 9,
                fontSize: 13,
                textDecoration: "none",
                fontWeight: active ? 600 : 400,
                color: active ? "var(--cv-text-on-dark)" : "var(--cv-text-on-dark-secondary)",
                background: active
                  ? "linear-gradient(90deg, rgba(91,141,239,0.24), rgba(91,141,239,0.05))"
                  : "transparent",
                borderLeft: active ? "2.5px solid var(--cv-accent-solid)" : "2.5px solid transparent",
              }}
            >
              <span style={{ color: active ? "#9cc0ff" : "var(--cv-text-on-dark-muted)", display: "inline-flex" }}>
                {link.icon}
              </span>
              {link.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
