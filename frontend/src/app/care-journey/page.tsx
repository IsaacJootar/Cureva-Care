import { Placeholder } from "@/components/layout/Placeholder";

export default function Page() {
  return (
    <Placeholder
      title="Care journey"
      subtitle="Booking, ANC contacts, delivery/PNC linkage"
      module="Module 4 (Maternal model & dashboards)"
      allowedRoles={["facility_lead", "organisation_user"]}
    />
  );
}
