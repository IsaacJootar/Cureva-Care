"use client";

import { useEffect, useState } from "react";
import { getSummary, type Summary } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { ChartPanel, MetricMeter } from "@/components/ui/Charts";
import { StatTileSkeleton } from "@/components/ui/Feedback";
import { ContinuumSection } from "@/components/dashboard/ContinuumSection";

export default function CareJourneyPage() {
  const [s, setS] = useState<Summary | null>(null);
  useEffect(() => {
    getSummary().then(setS).catch(() => setS(null));
  }, []);

  return (
    <AppShell title="Care journey" subtitle="How far women get along the path: register → check-ups → birth → after-birth care" allowedRoles={["facility_lead", "organisation_user"]}>
      {!s ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}><StatTileSkeleton /><StatTileSkeleton /></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <ChartPanel title="How well women are cared for">
            <MetricMeter label="Registered early (first 3 months)" ratio={s.metrics.early_anc_booking} tooltip="Share of women who registered their pregnancy in the first 3 months — earlier is better, problems get caught sooner." />
            <MetricMeter label="Had 4+ pregnancy check-ups" ratio={s.metrics.four_contact_completion} tooltip="Share of pregnancies with at least 4 recorded check-up visits." />
            <MetricMeter label="Completed 8+ check-ups (WHO standard)" ratio={s.metrics.eight_contact_completion} tooltip="The World Health Organization recommends at least 8 check-up visits in a healthy pregnancy. This is the share who reached that." />
            <MetricMeter label="Pregnancy care → gave birth here" ratio={s.care_journey.delivery_linkage} tooltip="Of women who had pregnancy check-ups, the share we can confirm gave birth at the facility." />
            <MetricMeter label="Came back after birth" ratio={s.care_journey.postnatal_linkage} tooltip="Of women who gave birth, the share who returned for an after-birth (postnatal) check-up." />
            <MetricMeter label="Tested (HIV, syphilis, anaemia)" ratio={s.metrics.screening_coverage} tooltip="Share of check-ups where at least one test (HIV, syphilis, or blood level) was recorded." />
            <MetricMeter label="Got preventives (iron, tetanus, malaria)" ratio={s.metrics.intervention_coverage} tooltip="Share of check-ups where a preventive treatment (iron/folate, tetanus shot, or malaria prevention) was recorded." />
            <MetricMeter label="Referrals followed up" ratio={s.metrics.referral_closure} tooltip="When a woman is referred to a bigger hospital, the share where we know the outcome." />
          </ChartPanel>

          <ContinuumSection />
        </div>
      )}
    </AppShell>
  );
}
