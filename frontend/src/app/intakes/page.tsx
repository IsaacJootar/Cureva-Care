"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Facility } from "@/lib/types";
import {
  createIntake,
  listFacilities,
  myIntakes,
  resolveMismatch,
  streamProgress,
  type Intake,
  type ProgressEvent,
  type RegisterFamily,
} from "@/lib/intake";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { SelectField, TextField } from "@/components/ui/Field";
import { EmptyState, StatusPill } from "@/components/ui/Feedback";
import { StatTile } from "@/components/ui/StatTile";
import { Table, Td, Th } from "@/components/ui/Table";
import { useToast } from "@/components/ui/Toast";
import {
  AlertTriangleIcon,
  BuildingIcon,
  CameraIcon,
  CheckIcon,
  ClockIcon,
  FileTextIcon,
  SearchIcon,
  SwapIcon,
  UploadIcon,
} from "@/components/icons";

const FAMILIES: RegisterFamily[] = ["ANC", "Delivery", "PNC"];
const FAMILY_LABEL: Record<RegisterFamily, string> = {
  ANC: "Antenatal (ANC)",
  Delivery: "Delivery",
  PNC: "Postnatal (PNC)",
};
const FAMILY_DESC: Record<RegisterFamily, string> = {
  ANC: "Antenatal care — pregnancy booking and check-up visits",
  Delivery: "Delivery / labour ward — birth outcomes",
  PNC: "Postnatal care — mother and baby after birth",
};
const STORAGE_KEY = "cv-do-facility";

type CardState = "idle" | "staged" | "extracting" | "done" | "mismatch";

export default function IntakesPage() {
  const [facility, setFacility] = useState<Facility | null>(null);

  // Restore the session's active facility.
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw) setFacility(JSON.parse(raw));
    } catch {
      /* ignore */
    }
  }, []);

  const selectFacility = (f: Facility | null) => {
    setFacility(f);
    try {
      if (f) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(f));
      else sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  };

  const title = facility ? facility.name : "Choose a facility to begin";
  const subtitle = facility
    ? `${[facility.state_name, facility.local_government_name].filter(Boolean).join(" · ")} · your active workspace`
    : "Search the index below, select one, and your workspace switches to it";

  return (
    <AppShell
      title={title}
      subtitle={subtitle}
      allowedRoles={["data_officer"]}
      action={
        facility ? (
          <Button variant="secondary" leftIcon={<SwapIcon size={15} />} onClick={() => selectFacility(null)}>
            Switch facility
          </Button>
        ) : undefined
      }
    >
      {facility ? (
        <ActiveWorkspace facility={facility} />
      ) : (
        <FacilityIndex onSelect={selectFacility} />
      )}
    </AppShell>
  );
}

function FacilityIndex({ onSelect }: { onSelect: (f: Facility) => void }) {
  const [facilities, setFacilities] = useState<Facility[] | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    listFacilities().then(setFacilities).catch(() => setFacilities([]));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!facilities) return [];
    if (!q) return facilities;
    return facilities.filter((f) =>
      [f.name, f.state_name, f.local_government_name].filter(Boolean).some((v) => v!.toLowerCase().includes(q)),
    );
  }, [facilities, query]);

  return (
    <div
      style={{
        background: "var(--cv-card-bg)",
        border: "1px solid var(--cv-card-border)",
        borderRadius: "var(--cv-radius-card)",
        boxShadow: "var(--cv-card-shadow)",
        padding: 18,
        maxWidth: 640,
      }}
    >
      <div style={{ position: "relative", marginBottom: 12 }}>
        <span style={{ position: "absolute", left: 11, top: 10, color: "var(--cv-text-muted)" }}>
          <SearchIcon size={15} />
        </span>
        <input
          placeholder="Search facilities by name, LGA, or state"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{
            width: "100%",
            padding: "9px 11px 9px 34px",
            borderRadius: "var(--cv-radius-control)",
            border: "1px solid var(--cv-input-border)",
            background: "var(--cv-input-bg)",
            color: "var(--cv-text-primary)",
            fontSize: 12.5,
            outline: "none",
          }}
        />
      </div>
      {facilities === null ? (
        <p style={{ color: "var(--cv-text-muted)", fontSize: 12.5 }}>Loading facilities…</p>
      ) : filtered.length === 0 ? (
        <EmptyState heading={query ? `No facilities match “${query}”` : "No facilities yet"} />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", maxHeight: 440, overflowY: "auto" }}>
          {filtered.map((f) => (
            <button
              key={f.id}
              onClick={() => onSelect(f)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 11,
                padding: "11px 8px",
                background: "transparent",
                border: "none",
                borderBottom: "1px solid var(--cv-hairline)",
                cursor: "pointer",
                textAlign: "left",
                width: "100%",
              }}
            >
              <span style={{ color: "var(--cv-text-muted)" }}><BuildingIcon size={16} /></span>
              <span style={{ flex: 1 }}>
                <span style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--cv-text-primary)" }}>
                  {f.name}
                </span>
                <span style={{ display: "block", fontSize: 11, color: "var(--cv-text-muted)" }}>
                  {[f.state_name, f.local_government_name].filter(Boolean).join(" · ")}
                </span>
              </span>
              <span style={{ color: "var(--cv-text-muted)" }}>›</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ActiveWorkspace({ facility }: { facility: Facility }) {
  const [history, setHistory] = useState<Intake[]>([]);

  const loadHistory = useCallback(() => {
    myIntakes(facility.id).then(setHistory).catch(() => setHistory([]));
  }, [facility.id]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const lastIntake = history[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, maxWidth: 760 }}>
        <StatTile status="neutral" icon={<FileTextIcon size={14} />} label="Intakes submitted" value={history.length} />
        <StatTile
          status={lastIntake ? "success" : "warning"}
          icon={<ClockIcon size={14} />}
          label="Last intake"
          value={lastIntake ? new Date(lastIntake.received_at).toLocaleDateString() : "None yet"}
        />
        <StatTile
          status="neutral"
          icon={<CheckIcon size={14} />}
          label="Published"
          value={history.filter((i) => i.status === "published").length}
        />
      </div>

      <IntakeCard facility={facility} onChanged={loadHistory} />

      <div>
        <h2 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", marginBottom: 10 }}>
          Your intake history at {facility.name}
        </h2>
        {history.length === 0 ? (
          <EmptyState icon={<FileTextIcon size={22} />} heading="No intakes yet at this facility" hint="Start one above." />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Register</Th>
                <Th>Submitted</Th>
                <Th>Rows</Th>
                <Th>Pages</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {history.map((i) => (
                <tr key={i.id}>
                  <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{i.register_family}</Td>
                  <Td>{new Date(i.received_at).toLocaleString()}</Td>
                  <Td><span className="cv-num">{i.row_count}</span></Td>
                  <Td><span className="cv-num">{i.page_count}</span></Td>
                  <Td><IntakeStatusPill status={i.status} /></Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>
    </div>
  );
}

function IntakeStatusPill({ status }: { status: string }) {
  const map: Record<string, { s: "success" | "warning" | "danger" | "neutral"; label: string }> = {
    published: { s: "success", label: "Published" },
    awaiting_confirmation: { s: "warning", label: "Awaiting confirmation" },
    extraction_failed: { s: "danger", label: "Extraction failed" },
    rejected: { s: "danger", label: "Rejected" },
  };
  const m = map[status] ?? { s: "neutral" as const, label: status };
  return <StatusPill status={m.s}>{m.label}</StatusPill>;
}

function IntakeCard({ facility, onChanged }: { facility: Facility; onChanged: () => void }) {
  const toast = useToast();
  const router = useRouter();
  const [state, setState] = useState<CardState>("idle");
  // No silent default — the officer must deliberately choose which register
  // they are entering before capture/upload unlocks (prevents uploading a
  // Delivery book while the form still says Antenatal).
  const [family, setFamily] = useState<RegisterFamily | "">("");
  const [files, setFiles] = useState<File[]>([]);
  const [sourceLabel, setSourceLabel] = useState<"upload" | "camera">("upload");
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");
  const [fieldStates, setFieldStates] = useState<{ field: string; label: string; state: string }[]>([]);
  const [summary, setSummary] = useState<{ matched: number; needs_mapping: string[]; row_count: number } | null>(null);
  const [mismatch, setMismatch] = useState<{ declared: string; suspected: string } | null>(null);
  const [intakeId, setIntakeId] = useState<string | null>(null);
  const [totalFields, setTotalFields] = useState(0);
  const captureRef = useRef<HTMLInputElement>(null);
  const uploadRef = useRef<HTMLInputElement>(null);

  // --- Front-end-paced "labour illusion" scan cascade -----------------------
  // The server does all the vision work up front and can fire every field
  // verdict in a burst. To keep the scan feeling live — reading one field at a
  // time, ticking each as it resolves — the stream only *feeds a queue*, and a
  // local pump reveals fields on a steady cadence no matter how fast they land.
  // The result summary is held back until the whole cascade has played out.
  const CADENCE_MS = 150; // gap between each field appearing
  const READ_MS = 460; // how long a field shows "reading…" before it ticks
  const queueRef = useRef<{ field: string; label: string; state: "matched" | "pending" }[]>([]);
  const finalRef = useRef<ProgressEvent | null>(null);
  const pumpRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const revealedRef = useRef(0);
  const flippedRef = useRef(0);

  const stopPump = useCallback(() => {
    if (pumpRef.current) {
      clearInterval(pumpRef.current);
      pumpRef.current = null;
    }
  }, []);

  useEffect(() => stopPump, [stopPump]);

  const reset = () => {
    stopPump();
    queueRef.current = [];
    finalRef.current = null;
    revealedRef.current = 0;
    flippedRef.current = 0;
    setState("idle");
    setFamily(""); // force a deliberate register choice for every new intake
    setFiles([]);
    setFieldStates([]);
    setTotalFields(0);
    setSummary(null);
    setMismatch(null);
    setIntakeId(null);
  };

  function onPick(list: FileList | null, label: "upload" | "camera") {
    if (!list || list.length === 0) return;
    setFiles(Array.from(list));
    setSourceLabel(label);
    setState("staged");
  }

  async function extract() {
    if (!family) {
      toast.warning("Select which register you're importing first.");
      return;
    }
    if (!periodFrom || !periodTo) {
      toast.warning("Set the batch service-date range first.");
      return;
    }
    setState("extracting");
    setFieldStates([]);
    try {
      const intake = await createIntake({
        facility: facility.id,
        register_family: family,
        batch_period_from: periodFrom,
        batch_period_to: periodTo,
        source_label: sourceLabel,
        files,
      });
      if (intake.detail?.startsWith("Duplicate")) {
        toast.info("This exact batch was already submitted (no-op).");
        reset();
        onChanged();
        return;
      }
      setIntakeId(intake.id);
      await streamProgress(intake.id, (e: ProgressEvent) => handleEvent(e));
      onChanged();
    } catch {
      toast.error("Could not start extraction. Please try again.");
      setState("staged");
    }
  }

  const applyFinal = useCallback((e: ProgressEvent) => {
    if (e.type === "mismatch") {
      setMismatch({ declared: e.declared, suspected: e.suspected });
      setState("mismatch");
    } else if (e.type === "done") {
      setSummary({ matched: e.matched, needs_mapping: e.needs_mapping, row_count: e.row_count });
      setState("done");
    }
  }, []);

  const startPump = useCallback(() => {
    stopPump();
    pumpRef.current = setInterval(() => {
      // Reveal the next queued field in "reading…", then tick it to its verdict.
      const next = queueRef.current.shift();
      if (next) {
        revealedRef.current += 1;
        setFieldStates((prev) => [...prev, { field: next.field, label: next.label, state: "reading" }]);
        setTimeout(() => {
          setFieldStates((prev) => prev.map((f) => (f.field === next.field ? { ...f, state: next.state } : f)));
          flippedRef.current += 1;
        }, READ_MS);
        return;
      }
      // Queue drained: once every revealed field has ticked, play the summary.
      if (finalRef.current && revealedRef.current > 0 && flippedRef.current >= revealedRef.current) {
        const fin = finalRef.current;
        finalRef.current = null;
        stopPump();
        applyFinal(fin);
      }
    }, CADENCE_MS);
  }, [applyFinal, stopPump]);

  function handleEvent(e: ProgressEvent) {
    if (e.type === "start") {
      setTotalFields(e.total_fields);
      setFieldStates([]);
      queueRef.current = [];
      finalRef.current = null;
      revealedRef.current = 0;
      flippedRef.current = 0;
      startPump();
    } else if (e.type === "field") {
      // Only queue resolved verdicts; the pump drives the reading→tick rhythm.
      if (e.state === "matched" || e.state === "pending") {
        queueRef.current.push({ field: e.field, label: e.label, state: e.state });
      }
    } else if (e.type === "mismatch" || e.type === "done") {
      finalRef.current = e; // held until the cascade finishes
    } else if (e.type === "extraction_failed") {
      stopPump();
      toast.error("Extraction failed. You can retry from your intake history.");
      setState("idle");
    }
  }

  async function onResolve(action: "confirm_declared" | "switch") {
    if (!intakeId) return;
    try {
      await resolveMismatch(intakeId, action);
      if (action === "switch") {
        toast.success("Switched register family and re-extracted.");
      } else {
        toast.success("Confirmed — proceeding with the declared register.");
      }
      setMismatch(null);
      // Reload rows summary by going to confirm screen.
      router.push(`/intakes/${intakeId}/confirm-fields`);
    } catch {
      toast.error("Could not resolve. Please try again.");
    }
  }

  return (
    <div
      style={{
        background: "var(--cv-card-bg)",
        border: "1px solid var(--cv-card-border)",
        borderRadius: "var(--cv-radius-card)",
        boxShadow: "var(--cv-card-shadow)",
        padding: 20,
        maxWidth: 760,
      }}
    >
      {/* The active register is stated boldly and stays visible through every
          step, so an officer can never lose track of which book they are
          entering (they must pick one before capture/upload unlocks). */}
      {family && <ActiveRegisterBanner family={family} locked={state !== "idle" && state !== "staged"} />}

      {/* Register family + period (declared at the start of the intake). */}
      {(state === "idle" || state === "staged") && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 12 }}>
            <SelectField
              id="register-family"
              label="Which register are you importing? (required)"
              value={family}
              onChange={(e) => setFamily(e.target.value as RegisterFamily | "")}
            >
              <option value="" disabled>
                Select a register…
              </option>
              {FAMILIES.map((f) => (
                <option key={f} value={f}>
                  {FAMILY_LABEL[f]}
                </option>
              ))}
            </SelectField>
            {family && (
              <p style={{ fontSize: 11, color: "var(--cv-text-muted)", margin: "6px 2px 0" }}>
                {FAMILY_DESC[family]}
              </p>
            )}
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <TextField id="from" label="Service dates from" type="date" value={periodFrom} onChange={(e) => setPeriodFrom(e.target.value)} />
            </div>
            <div style={{ flex: 1 }}>
              <TextField id="to" label="to" type="date" value={periodTo} onChange={(e) => setPeriodTo(e.target.value)} />
            </div>
          </div>
        </div>
      )}

      {state === "idle" && (
        <>
          {!family && (
            <p style={{ fontSize: 12, color: "var(--cv-text-muted)", textAlign: "center", margin: "0 0 12px" }}>
              Select the register above to unlock capture &amp; upload.
            </p>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <input ref={captureRef} type="file" accept="image/*" capture="environment" multiple hidden onChange={(e) => onPick(e.target.files, "camera")} />
            <input ref={uploadRef} type="file" accept="image/*" multiple hidden onChange={(e) => onPick(e.target.files, "upload")} />
            <StageTile icon={<CameraIcon size={22} />} title="Capture Register" desc="Photograph the register page with this device's camera." disabled={!family} onClick={() => captureRef.current?.click()} />
            <StageTile icon={<UploadIcon size={22} />} title="Upload Register" desc="Upload an existing photo of the register page." disabled={!family} onClick={() => uploadRef.current?.click()} />
          </div>
        </>
      )}

      {state === "staged" && (
        <div>
          <h3 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: "0 0 4px" }}>Review before extracting</h3>
          <p style={{ fontSize: 11.5, color: "var(--cv-text-muted)", margin: "0 0 12px" }}>
            {sourceLabel === "camera" ? "Captured just now · this device's camera" : "Uploaded photo"}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
            {files.map((f, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 11px", border: "1px solid var(--cv-card-border)", borderRadius: 8 }}>
                <FileTextIcon size={16} />
                <span style={{ flex: 1, fontSize: 12.5, color: "var(--cv-text-primary)" }}>{family ? FAMILY_LABEL[family] : ""} register — page {i + 1}</span>
                <span style={{ fontSize: 11, color: "var(--cv-success-text)" }}>Ready for extraction</span>
                <button onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))} style={{ background: "none", border: "none", color: "var(--cv-button-danger-bg)", cursor: "pointer", fontSize: 11.5 }}>Remove</button>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <Button variant="secondary" onClick={reset}>Cancel</Button>
            <Button fullWidth onClick={extract} disabled={files.length === 0}>Extract</Button>
          </div>
        </div>
      )}

      {state === "extracting" && (() => {
        const read = fieldStates.filter((f) => f.state !== "reading").length;
        const scanningImage = fieldStates.length === 0;
        return (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 10 }}>
              <span className="cv-spin" style={{ width: 14, height: 14, borderRadius: "50%", border: "2px solid var(--cv-accent-soft)", borderTopColor: "var(--cv-accent-solid)", display: "inline-block" }} />
              <h3 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: 0 }}>
                {scanningImage ? "Reading the register image…" : "Scanning & matching fields…"}
              </h3>
              {!scanningImage && totalFields > 0 && (
                <span className="cv-num" style={{ marginLeft: "auto", fontSize: 11.5, color: "var(--cv-text-muted)" }}>
                  {read} of {totalFields} fields read
                </span>
              )}
            </div>
            {!scanningImage && totalFields > 0 && (
              <div style={{ height: 4, borderRadius: 4, background: "var(--cv-accent-soft)", overflow: "hidden", marginBottom: 12 }}>
                <div style={{ height: "100%", width: `${Math.round((read / totalFields) * 100)}%`, background: "var(--cv-accent-solid)", transition: "width .3s ease" }} />
              </div>
            )}
            <FieldChecklist fields={fieldStates} />
          </div>
        );
      })()}

      {state === "mismatch" && mismatch && (
        <div style={{ background: "var(--cv-warning-bg)", border: "1px solid var(--cv-warning-border)", borderRadius: 10, padding: 16 }}>
          <div style={{ display: "flex", gap: 9, alignItems: "flex-start" }}>
            <span style={{ color: "var(--cv-warning-icon)" }}><AlertTriangleIcon size={18} /></span>
            <div>
              <h3 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: "0 0 4px" }}>
                This looks like it might be a {mismatch.suspected} register, not {mismatch.declared}.
              </h3>
              <p style={{ fontSize: 11.5, color: "var(--cv-text-secondary)", margin: "0 0 14px" }}>
                Check the photo and choose how to proceed.
              </p>
              <div style={{ display: "flex", gap: 10 }}>
                <Button variant="secondary" onClick={() => onResolve("confirm_declared")}>Confirm {mismatch.declared} is correct</Button>
                <Button onClick={() => onResolve("switch")}>Switch to {mismatch.suspected}</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {state === "done" && summary && (
        <div>
          <FieldChecklist fields={fieldStates} />
          <div style={{ marginTop: 14, padding: "12px 14px", background: "var(--cv-success-bg)", border: "1px solid var(--cv-success-border)", borderRadius: 10 }}>
            <span style={{ fontSize: 12.5, color: "var(--cv-success-text)", fontWeight: 600 }}>
              Extraction complete — {summary.row_count} row{summary.row_count === 1 ? "" : "s"}, {summary.matched} fields matched
              {summary.needs_mapping.length > 0 ? ` · ${summary.needs_mapping.length} need mapping` : ""}.
            </span>
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
            <Button variant="secondary" onClick={reset}>Start another intake</Button>
            <Button onClick={() => intakeId && router.push(`/intakes/${intakeId}/confirm-fields`)}>Confirm &amp; review fields</Button>
          </div>
        </div>
      )}
    </div>
  );
}

function StageTile({ icon, title, desc, onClick, disabled }: { icon: React.ReactNode; title: string; desc: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
        padding: "26px 18px",
        border: "1.5px dashed var(--cv-empty-border)",
        borderRadius: "var(--cv-radius-card)",
        background: "transparent",
        cursor: disabled ? "not-allowed" : "pointer",
        textAlign: "center",
        opacity: disabled ? 0.45 : 1,
      }}
    >
      <span style={{ color: "var(--cv-accent-solid)" }}>{icon}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--cv-text-primary)" }}>{title}</span>
      <span style={{ fontSize: 11, color: "var(--cv-text-muted)" }}>{desc}</span>
    </button>
  );
}

function ActiveRegisterBanner({ family, locked }: { family: RegisterFamily; locked: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 11,
        padding: "11px 14px",
        marginBottom: 16,
        borderRadius: 10,
        background: "var(--cv-accent-soft)",
        border: "1px solid var(--cv-accent-solid)",
      }}
    >
      <span style={{ color: "var(--cv-accent-solid)" }}><FileTextIcon size={18} /></span>
      <div style={{ flex: 1 }}>
        <span style={{ display: "block", fontSize: 10.5, fontWeight: 600, letterSpacing: 0.4, textTransform: "uppercase", color: "var(--cv-text-muted)" }}>
          You are importing
        </span>
        <span style={{ display: "block", fontSize: 14, fontWeight: 700, color: "var(--cv-text-primary)" }}>
          {FAMILY_LABEL[family]} register
        </span>
      </div>
      {locked && (
        <span style={{ fontSize: 10.5, fontWeight: 600, color: "var(--cv-text-muted)" }}>locked for this batch</span>
      )}
    </div>
  );
}

function FieldChecklist({ fields }: { fields: { field: string; label: string; state: string }[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {fields.map((f) => (
        <div key={f.field} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 2px", fontSize: 12.5 }}>
          <Indicator state={f.state} />
          <span style={{ flex: 1, color: "var(--cv-text-primary)" }}>{f.label}</span>
          {f.state === "reading" && <span style={{ fontSize: 11, color: "var(--cv-accent-solid)" }}>reading…</span>}
          {f.state === "pending" && <span style={{ fontSize: 11, color: "var(--cv-warning-text)" }}>needs mapping</span>}
        </div>
      ))}
    </div>
  );
}

function Indicator({ state }: { state: string }) {
  if (state === "matched")
    return <span style={{ color: "var(--cv-success-icon)" }}><CheckIcon size={15} /></span>;
  if (state === "pending")
    return <span style={{ color: "var(--cv-warning-icon)" }}><AlertTriangleIcon size={14} /></span>;
  if (state === "reading")
    return (
      <span className="cv-spin" style={{ width: 13, height: 13, borderRadius: "50%", border: "2px solid var(--cv-accent-soft)", borderTopColor: "var(--cv-accent-solid)", display: "inline-block" }} />
    );
  return <span style={{ width: 13, height: 13, borderRadius: "50%", border: "2px solid var(--cv-toggle-off)", display: "inline-block" }} />;
}
