"""Authoritative registry of tunable platform settings.

Every tunable operational value in the build is declared here, with its type,
default, and admin-facing description. This is the one place these defaults
live; the data migration seeds them, the admin screen lists them, and the
accessor (services.py) reads them. A literal threshold/delay/channel anywhere
else in the codebase is a defect (cureva-docs/02-data-model.md,
04-architecture-and-stack.md).
"""

# Keys (import these rather than typing the string literal at a call site).
STALE_FACILITY_ALERT_DAYS = "stale_facility_alert_days"
IDENTITY_CANDIDATE_CONFIDENCE_THRESHOLD = "identity_candidate_confidence_threshold"
AI_EXTRACTION_CONFIDENCE_THRESHOLD = "ai_extraction_confidence_threshold"
REGISTER_MISMATCH_MIN_SIGNAL = "register_mismatch_min_signal"

# value_type matches identity_access.models.PlatformSetting.ValueType.
SETTING_DEFINITIONS = [
    {
        "key": STALE_FACILITY_ALERT_DAYS,
        "value": 14,
        "value_type": "integer",
        "description": (
            "Days a facility may go without a new intake before a "
            "stale-facility alert fires."
        ),
    },
    {
        "key": IDENTITY_CANDIDATE_CONFIDENCE_THRESHOLD,
        "value": 0.75,
        "value_type": "decimal",
        "description": (
            "Minimum match confidence (0-1) at which a probabilistic identity "
            "candidate is surfaced to a Facility lead for confirmation. "
            "Starting default; tune from pilot confirm/reject rates."
        ),
    },
    {
        "key": AI_EXTRACTION_CONFIDENCE_THRESHOLD,
        "value": 0.85,
        "value_type": "decimal",
        "description": (
            "Field extraction confidence (0-1) below which an AI/OCR-read "
            "field is flagged for mandatory human confirmation before publish."
        ),
    },
    {
        "key": REGISTER_MISMATCH_MIN_SIGNAL,
        "value": 2,
        "value_type": "integer",
        "description": (
            "Minimum matched signature fields of another register family "
            "before the register-family cross-check flags a suspected wrong "
            "register."
        ),
    },
]

DEFAULTS_BY_KEY = {d["key"]: d for d in SETTING_DEFINITIONS}
