"use client";

import { useEffect, useState } from "react";
import { getSummary, type Summary } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { ChartPanel, Funnel, MetricMeter } from "@/components/ui/Charts";
import { StatTileSkeleton } from "@/components/ui/Feedback";

export default function CareJourneyPage() {
  const [s, setS] = useState<Summary | null>(null);
  useEffect(() => {
    getSummary().then(setS).catch(() => setS(null));
  }, []);

  return (
    <AppShell title="Care journey" subtitle="Booking, ANC contacts, delivery and PNC linkage" allowedRoles={["facility_lead", "organisation_user"]}>
      {!s ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}><StatTileSkeleton /><StatTileSkeleton /></div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, maxWidth: 900 }}>
          <ChartPanel title="Care-journey funnel">
            <Funnel stages={[
              { label: "Booked episodes", value: s.care_journey.booked_episodes },
              { label: "ANC contacts", value: s.care_journey.anc_contacts },
              { label: "Deliveries", value: s.care_journey.deliveries },
              { label: "PNC contacts", value: s.care_journey.pnc_contacts },
            ]} />
          </ChartPanel>
          <ChartPanel title="Continuity & coverage">
            <MetricMeter label="Early ANC booking" ratio={s.metrics.early_anc_booking} tooltip="Episodes booked in the first trimester (≤12 weeks), of episodes with a recorded booking gestational age." />
            <MetricMeter label="4+ ANC contacts" ratio={s.metrics.four_contact_completion} />
            <MetricMeter label="8+ ANC contacts (WHO)" ratio={s.metrics.eight_contact_completion} tooltip="WHO's eight-antenatal-contact model." />
            <MetricMeter label="ANC → Delivery linkage" ratio={s.care_journey.delivery_linkage} />
            <MetricMeter label="Delivery → PNC linkage" ratio={s.care_journey.postnatal_linkage} />
            <MetricMeter label="Screening coverage" ratio={s.metrics.screening_coverage} tooltip="ANC contacts with any recorded HIV, syphilis, or haemoglobin result." />
            <MetricMeter label="Intervention coverage" ratio={s.metrics.intervention_coverage} tooltip="ANC contacts with iron/folate, tetanus, or IPTp recorded." />
            <MetricMeter label="Referral closure" ratio={s.metrics.referral_closure} />
          </ChartPanel>
        </div>
      )}
    </AppShell>
  );
}
