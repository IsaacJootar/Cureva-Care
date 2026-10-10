import { Placeholder } from "@/components/layout/Placeholder";

export default function Page() {
  return (
    <Placeholder
      title="Settings"
      subtitle="Every tunable value in the platform, in one place"
      module="Module 6 (Operations & hardening)"
      allowedRoles={["systems_admin"]}
    />
  );
}
