"""Type/structure validation and plausibility checks.

Type mismatches are flagged (not silently coerced away); implausible values are
flagged as warnings and still publish once verified — a human decides
(cureva-docs/03 step 5-6, 06 "Data-quality sanity checks"). Blank means
unknown, never a negative result (rule #6): a missing field is simply absent,
never flagged.
"""
import re
from datetime import date, datetime

_TRUE = {"yes", "y", "true", "1", "given", "done", "✓"}
_FALSE = {"no", "n", "false", "0", "not given", "none"}
_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%m/%d/%Y"]


def _coerce(value, col):
    """Return (normalized_value, type_ok). Blank/None -> (None, True)."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, True

    t = col["type"]
    s = str(value).strip()

    if t == "string":
        return s, True
    if t == "integer":
        m = re.search(r"-?\d+", s)
        return (int(m.group()), True) if m else (s, False)
    if t == "decimal":
        m = re.search(r"-?\d+(\.\d+)?", s)
        return (float(m.group()), True) if m else (s, False)
    if t == "boolean":
        low = s.lower()
        if low in _TRUE:
            return True, True
        if low in _FALSE:
            return False, True
        return s, False
    if t == "date":
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt).date().isoformat(), True
            except ValueError:
                continue
        return s, False
    if t == "enum":
        allowed = col.get("enum_values", [])
        for a in allowed:
            if s.lower() == a.lower():
                return a, True
        return s, False
    return s, True


def _plausible(value, plausible_range, canonical_field):
    """Return None if plausible/unchecked, else a warning message."""
    if value is None or plausible_range is None:
        return None

    # Blood pressure: "systolic 70-260 / diastolic 40-160" against "120/80".
    if "systolic" in plausible_range and "diastolic" in plausible_range:
        nums = re.findall(r"\d+", plausible_range)
        if len(nums) >= 4:
            s_lo, s_hi, d_lo, d_hi = map(int, nums[:4])
            m = re.match(r"\s*(\d+)\s*/\s*(\d+)", str(value))
            if m:
                sys_v, dia_v = int(m.group(1)), int(m.group(2))
                if not (s_lo <= sys_v <= s_hi and d_lo <= dia_v <= d_hi):
                    return f"Blood pressure {value} is outside the plausible range."
        return None

    # Simple numeric range "lo-hi".
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$", plausible_range)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        try:
            num = float(re.search(r"-?\d+(\.\d+)?", str(value)).group())
        except (AttributeError, ValueError):
            return None
        if not (lo <= num <= hi):
            return f"{canonical_field.replace('_', ' ').title()} value {value} is outside the plausible range ({plausible_range})."
    return None


def validate_and_normalize(template: dict, matched_fields: dict) -> dict:
    """Validate matched fields against their declared types and plausibility
    ranges. Returns {'normalized': {...}, 'flags': {field: {...}}}."""
    cols = {c["canonical_field"]: c for c in template["columns"]}
    normalized, flags = {}, {}

    for field, raw in matched_fields.items():
        col = cols.get(field)
        if col is None:
            continue  # unmatched handled upstream
        value, type_ok = _coerce(raw, col)
        normalized[field] = value
        if not type_ok:
            flags[field] = {"kind": "type_error", "message": f"Could not read '{raw}' as {col['type']}.", "raw": raw}
            continue
        warn = _plausible(value, col.get("plausible_range"), field)
        if warn:
            flags[field] = {"kind": "implausible", "message": warn, "raw": raw}

    return {"normalized": normalized, "flags": flags}


def service_date_from_normalized(register_family: str, normalized: dict):
    """Pick the clinical service date for a row by register family (rule #4:
    service_date drives everything, never upload date)."""
    key = {"ANC": "service_date", "Delivery": "delivery_date", "PNC": "visit_date"}.get(register_family)
    # ANC rows don't carry a single service_date column in the default template;
    # fall back to next_appointment's sibling — here the contact date is the
    # intake-level period; callers may override. Use the explicit key if present.
    candidates = [key, "service_date", "visit_date", "delivery_date"]
    for k in candidates:
        if k and normalized.get(k):
            try:
                return date.fromisoformat(normalized[k])
            except (ValueError, TypeError):
                continue
    return None
