"use client";

import { AppShell } from "./AppShell";
import { EmptyState } from "../ui/Feedback";
import { LayersIcon } from "../icons";
import type { Role } from "@/lib/types";

// Empty, correctly-scoped shell for routes whose full build lands in a later
// module. Keeps every nav link resolving (no 404s) and the design system
// applied, per Module 1 section 12.
export function Placeholder({
  title,
  subtitle,
  module,
  allowedRoles,
}: {
  title: string;
  subtitle?: string;
  module: string;
  allowedRoles?: Role[];
}) {
  return (
    <AppShell title={title} subtitle={subtitle} allowedRoles={allowedRoles}>
      <EmptyState
        icon={<LayersIcon size={24} />}
        heading={`${title} — coming in ${module}`}
        hint="This screen's shell and navigation are in place. Its full functionality is built in the module noted above, against this same design system."
      />
    </AppShell>
  );
}
