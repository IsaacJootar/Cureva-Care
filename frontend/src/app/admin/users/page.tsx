import { Placeholder } from "@/components/layout/Placeholder";

export default function Page() {
  return (
    <Placeholder
      title="Users & roles"
      subtitle="User and role management"
      module="Module 6 (Operations & hardening)"
      allowedRoles={["systems_admin"]}
    />
  );
}
