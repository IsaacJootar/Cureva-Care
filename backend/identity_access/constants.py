"""Shared constants for Identity & Access.

NOTIFICATION_TYPES is the authoritative list of notification types the product
sends. Every user gets a default notification_preferences row per type at
creation (cureva-docs/02-data-model.md). Adding a type later means adding it
here; no notification job ever hard-codes a channel.
"""

STALE_FACILITY_ALERT = "stale_facility_alert"

NOTIFICATION_TYPES = [
    STALE_FACILITY_ALERT,
]
