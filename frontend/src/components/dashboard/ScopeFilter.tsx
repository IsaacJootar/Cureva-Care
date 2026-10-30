"use client";

import { useEffect, useState } from "react";
import { getScopeOptions, type ScopeOptions, type ScopeSel } from "@/lib/dashboard";
import { SelectField } from "@/components/ui/Field";

/** Dashboard scope selector: "All facilities", a whole state, or one facility.
 * Hides itself when the caller has only a single facility (nothing to pick).
 * The selection only ever narrows the caller's scope; the server enforces it. */
export function ScopeFilter({ value, onChange }: { value: ScopeSel; onChange: (s: ScopeSel) => void }) {
  const [opts, setOpts] = useState<ScopeOptions | null>(null);

  useEffect(() => {
    getScopeOptions().then(setOpts).catch(() => setOpts(null));
  }, []);

  if (!opts || opts.facilities.length <= 1) return null;

  const current = value.facility ? `facility:${value.facility}` : value.state ? `state:${value.state}` : "";
  const multiState = opts.states.length > 1;

  return (
    <div style={{ width: 230 }}>
      <SelectField
        id="scope"
        label=""
        value={current}
        onChange={(e) => {
          const v = e.target.value;
          if (v.startsWith("facility:")) onChange({ facility: v.slice(9) });
          else if (v.startsWith("state:")) onChange({ state: v.slice(6) });
          else onChange({});
        }}
      >
        <option value="">All facilities in scope</option>
        {multiState &&
          opts.states.map((s) => <option key={`s-${s.id}`} value={`state:${s.id}`}>All of {s.name}</option>)}
        {opts.facilities.map((f) => (
          <option key={f.id} value={`facility:${f.id}`}>
            {f.name}
            {multiState ? ` · ${f.state}` : ""}
          </option>
        ))}
      </SelectField>
    </div>
  );
}
