import { Placeholder } from "@/components/layout/Placeholder";

export default function Page() {
  return (
    <Placeholder
      title="Facilities"
      subtitle="Readiness, reporting, quality, comparison"
      module="Module 4 (Maternal model & dashboards)"
      allowedRoles={["facility_lead", "organisation_user"]}
    />
  );
}
