import { Placeholder } from "@/components/layout/Placeholder";

export default function Page() {
  return (
    <Placeholder
      title="Identity review"
      subtitle="Candidate identity matches awaiting confirmation"
      module="Module 3 (Identity linkage)"
      allowedRoles={["facility_lead"]}
    />
  );
}
