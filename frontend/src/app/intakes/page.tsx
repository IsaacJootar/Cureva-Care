import { Placeholder } from "@/components/layout/Placeholder";

export default function Page() {
  return (
    <Placeholder
      title="New intake"
      subtitle="Capture or upload a photographed register"
      module="Module 2 (Intake & templates)"
      allowedRoles={["data_officer"]}
    />
  );
}
