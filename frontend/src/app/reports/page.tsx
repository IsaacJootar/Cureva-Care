import { Placeholder } from "@/components/layout/Placeholder";

export default function Page() {
  return (
    <Placeholder
      title="Reports"
      subtitle="Saved briefs and dataset exports"
      module="Module 5 (Risk, referrals & reporting)"
      allowedRoles={["facility_lead", "organisation_user"]}
    />
  );
}
