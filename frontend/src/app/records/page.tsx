"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { getRecords, type RecordRow } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import { EmptyState, StatusPill, StatTileSkeleton } from "@/components/ui/Feedback";
import { Pagination, Table, Td, Th } from "@/components/ui/Table";
import { AlertTriangleIcon, FileTextIcon } from "@/components/icons";

export default function RecordsPage() {
  const [data, setData] = useState<{ results: RecordRow[]; count: number; page: number; page_size: number } | null>(null);
  const [page, setPage] = useState(1);
  const [aggregate, setAggregate] = useState(false);

  const load = useCallback((p: number) => {
    getRecords(p)
      .then(setData)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 403) setAggregate(true);
        else setData({ results: [], count: 0, page: 1, page_size: 25 });
      });
  }, []);

  useEffect(() => {
    load(page);
  }, [load, page]);

  if (aggregate) {
    return (
      <AppShell title="Records" subtitle="The individual verified records behind the numbers" allowedRoles={["facility_lead", "organisation_user"]}>
        <EmptyState
          icon={<AlertTriangleIcon size={24} />}
          heading="Individual records aren't included in your plan"
          hint="Your organisation can see totals and charts, but not individual mothers' records. Ask a Cureva Care administrator if you need access to the records themselves."
        />
      </AppShell>
    );
  }

  const pageCount = data ? Math.max(1, Math.ceil(data.count / data.page_size)) : 1;

  return (
    <AppShell
      title="Records"
      subtitle={data ? `${data.count} verified records` : "Loading…"}
      allowedRoles={["facility_lead", "organisation_user"]}
    >
      {!data ? (
        <div className="cv-stat-grid">
          {Array.from({ length: 3 }).map((_, i) => <StatTileSkeleton key={i} />)}
        </div>
      ) : data.results.length === 0 ? (
        <EmptyState icon={<FileTextIcon size={24} />} heading="No verified records yet" hint="Once records are checked and published, they appear here exactly as written in the register." />
      ) : (
        <>
          <Table>
            <thead>
              <tr>
                <Th>Register</Th>
                <Th>Service date</Th>
                <Th>Key values</Th>
                <Th>Flags</Th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((r) => {
                const keyVals = Object.entries(r.values).filter(([, v]) => v != null && v !== "").slice(0, 4);
                return (
                  <tr key={r.id}>
                    <Td style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{r.register_family}</Td>
                    <Td className="cv-num">{r.service_date ?? "—"}</Td>
                    <Td>
                      {keyVals.map(([k, v]) => (
                        <span key={k} style={{ marginRight: 10, fontSize: 11.5 }}>
                          <span style={{ color: "var(--cv-text-muted)" }}>{k.replace(/_/g, " ")}: </span>
                          <span style={{ color: "var(--cv-text-secondary)" }}>{String(v)}</span>
                        </span>
                      ))}
                    </Td>
                    <Td>{r.flags && Object.keys(r.flags).length > 0 ? <StatusPill status="warning">{Object.keys(r.flags).length} flag(s)</StatusPill> : "—"}</Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
          <Pagination page={data.page} pageCount={pageCount} total={data.count} pageSize={data.page_size} onPage={setPage} />
        </>
      )}
    </AppShell>
  );
}
