import { Placeholder } from "@/components/layout/Placeholder";

export default function Page() {
  return (
    <Placeholder
      title="My organisation's users"
      subtitle="Invite and manage your organisation's users"
      module="Module 4 (Maternal model & dashboards)"
      allowedRoles={["organisation_user"]}
    />
  );
}
