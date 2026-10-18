import type { ReactNode } from "react";
import {
  ActivityIcon,
  AlertTriangleIcon,
  BarChartIcon,
  BuildingIcon,
  CheckIcon,
  FileTextIcon,
  HeartPulseIcon,
  LayersIcon,
  SettingsIcon,
  ShieldIcon,
  UploadIcon,
  UsersIcon,
} from "@/components/icons";
import type { CurrentUser, Role } from "./types";

export interface NavLink {
  label: string;
  href: string;
  icon: ReactNode;
  badgeKey?: "identity_pending";
}
export interface NavGroup {
  label?: string;
  links: NavLink[];
}
export interface RoleNav {
  contextRow?: { title: string; caption: string };
  groups: NavGroup[];
}

// Where each role lands after sign-in. Systems admins have no dashboard
// (least privilege) — they land on an admin screen (cureva-docs/01, 09).
export function roleLanding(role: Role): string {
  switch (role) {
    case "systems_admin":
      return "/admin/organisations";
    case "data_officer":
      return "/intakes";
    default:
      return "/overview"; // facility_lead, organisation_user
  }
}

// Nav per role (cureva-docs/09 "Navigation map"). Role navs do not overlap.
export function navForUser(user: CurrentUser): RoleNav {
  switch (user.role) {
    case "systems_admin":
      return {
        groups: [
          {
            label: "ADMIN",
            links: [
              { label: "Templates", href: "/admin/templates", icon: <LayersIcon size={16} /> },
              { label: "Manage facilities", href: "/admin/facilities", icon: <BuildingIcon size={16} /> },
              { label: "Organisations", href: "/admin/organisations", icon: <ShieldIcon size={16} /> },
              { label: "Users & roles", href: "/admin/users", icon: <UsersIcon size={16} /> },
              { label: "Settings", href: "/admin/settings", icon: <SettingsIcon size={16} /> },
            ],
          },
        ],
      };

    case "facility_lead":
      return {
        contextRow: {
          title: user.facility_name ?? "Your facility",
          caption: "Locked to your assignment",
        },
        groups: [
          {
            label: "MY FACILITY",
            links: [
              { label: "Overview", href: "/overview", icon: <BarChartIcon size={16} /> },
              { label: "Care journey", href: "/care-journey", icon: <ActivityIcon size={16} /> },
              { label: "Benchmarking", href: "/benchmarking", icon: <LayersIcon size={16} /> },
              { label: "Deaths & stillbirths", href: "/surveillance", icon: <ShieldIcon size={16} /> },
              { label: "Risk & alerts", href: "/risk", icon: <AlertTriangleIcon size={16} /> },
              { label: "Needs attention", href: "/needs-attention", icon: <HeartPulseIcon size={16} /> },
              { label: "Outcomes", href: "/outcomes", icon: <HeartPulseIcon size={16} /> },
              { label: "Data quality (RDQA)", href: "/rdqa", icon: <CheckIcon size={16} /> },
              { label: "Records", href: "/records", icon: <FileTextIcon size={16} /> },
              { label: "Reports", href: "/reports", icon: <FileTextIcon size={16} /> },
            ],
          },
          {
            label: "REVIEW",
            links: [
              {
                label: "Identity review",
                href: "/identity-review",
                icon: <UsersIcon size={16} />,
                badgeKey: "identity_pending",
              },
            ],
          },
        ],
      };

    case "organisation_user": {
      const groups: NavGroup[] = [
        {
          label: "MAIN",
          links: [
            { label: "Overview", href: "/overview", icon: <BarChartIcon size={16} /> },
            { label: "Care journey", href: "/care-journey", icon: <ActivityIcon size={16} /> },
            { label: "Benchmarking", href: "/benchmarking", icon: <LayersIcon size={16} /> },
            { label: "Deaths & stillbirths", href: "/surveillance", icon: <ShieldIcon size={16} /> },
            { label: "Risk & alerts", href: "/risk", icon: <AlertTriangleIcon size={16} /> },
            { label: "Outcomes", href: "/outcomes", icon: <HeartPulseIcon size={16} /> },
            { label: "Facilities", href: "/facilities", icon: <BuildingIcon size={16} /> },
            { label: "Data quality (RDQA)", href: "/rdqa", icon: <CheckIcon size={16} /> },
            { label: "Records", href: "/records", icon: <FileTextIcon size={16} /> },
            { label: "Reports", href: "/reports", icon: <FileTextIcon size={16} /> },
          ],
        },
      ];
      if (user.can_manage_org_users) {
        groups.push({
          label: "ORGANISATION",
          links: [{ label: "My organisation's users", href: "/org/users", icon: <UsersIcon size={16} /> }],
        });
      }
      return { groups };
    }

    case "data_officer":
      return {
        groups: [
          {
            label: "INTAKE",
            links: [
              { label: "New intake", href: "/intakes", icon: <UploadIcon size={16} /> },
              { label: "Intake history", href: "/intakes?view=history", icon: <FileTextIcon size={16} /> },
            ],
          },
        ],
      };
  }
}
