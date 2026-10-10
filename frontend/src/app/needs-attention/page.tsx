import { Placeholder } from "@/components/layout/Placeholder";

// Facility-lead-only (cureva-docs/09 screen 12). Not on an Organisation user's
// nav, and GET /api/v1/worklists rejects an Organisation user server-side.
export default function Page() {
  return (
    <Placeholder
      title="Needs attention"
      subtitle="Actionable worklists with rule reasons"
      module="Module 5 (Risk, referrals & reporting)"
      allowedRoles={["facility_lead"]}
    />
  );
}
