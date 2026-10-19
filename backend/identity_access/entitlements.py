"""Intelligence module entitlements (11-intelligence-module.md).

Each intelligence area is a gateable MODULE — a link on the sidebar and the
endpoints behind it. A paying organisation is subscribed to a configurable TIER
(a bundle of modules, admin-editable) plus any individual add-on modules. This
module is the one source of the module catalogue and the rule for resolving what
a given user may access, enforced on every intelligence request (never trusted
from the client).

Facility staff (facility leads) are internal to their own facility and see the
full set; tiers gate the paying organisation accounts.
"""

# Canonical catalogue. `href` is the sidebar link the module gates; `order` is
# the default display order (an admin can reorder within a tier).
INTEL_MODULES = [
    {"key": "overview", "label": "Overview", "href": "/overview", "order": 1},
    {"key": "care_journey", "label": "Care journey", "href": "/care-journey", "order": 2},
    {"key": "benchmarking", "label": "Benchmarking", "href": "/benchmarking", "order": 3},
    {"key": "surveillance", "label": "Deaths & stillbirths", "href": "/surveillance", "order": 4},
    {"key": "risk", "label": "Risk & alerts", "href": "/risk", "order": 5},
    {"key": "rdqa", "label": "Data quality (RDQA)", "href": "/rdqa", "order": 6},
    {"key": "reports", "label": "Reports", "href": "/reports", "order": 7},
    {"key": "records", "label": "Records", "href": "/records", "order": 8},
    {"key": "facilities", "label": "Facilities", "href": "/facilities", "order": 9},
]
MODULE_KEYS = {m["key"] for m in INTEL_MODULES}

# Sensible default composition for the three seeded tiers (admin-editable after).
DEFAULT_TIERS = [
    {"name": "Essentials", "slug": "essentials", "order": 1,
     "modules": ["overview", "care_journey", "reports"]},
    {"name": "Professional", "slug": "professional", "order": 2,
     "modules": ["overview", "care_journey", "benchmarking", "rdqa", "facilities", "reports"]},
    {"name": "Enterprise", "slug": "enterprise", "order": 3,
     "modules": ["overview", "care_journey", "benchmarking", "surveillance", "risk", "rdqa", "records", "facilities", "reports"]},
]


def entitled_modules(user) -> set:
    """The set of module keys a user may access."""
    role = getattr(user, "role", None)
    if role == "facility_lead":
        return set(MODULE_KEYS)  # internal staff: full set for their own facility
    if role == "organisation_user":
        org = getattr(user, "organisation", None)
        if org is None:
            return set()
        mods = set(org.tier.modules or []) if org.tier_id else set()
        mods |= set(org.extra_modules or [])
        return mods & MODULE_KEYS
    # systems_admin (admin screens) and data_officer (intake) are not dashboard
    # consumers; they reach the intelligence API only incidentally.
    return set()


def has_module(user, module_key) -> bool:
    if module_key is None:
        return True
    return module_key in entitled_modules(user)


# Map an API path to the module that gates it. Order matters: first fragment that
# appears in the path wins. A path not listed here is ungated (e.g. /workspace,
# which the app needs to boot and which returns the user's entitled modules).
PATH_MODULES = [
    ("/continuum/", "care_journey"),
    ("/care-journey", "care_journey"),
    ("/benchmarking", "benchmarking"),
    ("/geo", "benchmarking"),
    ("/equity", "benchmarking"),
    ("/surveillance/", "surveillance"),
    ("/risk/", "risk"),
    ("/alerts", "risk"),
    ("/rdqa/", "rdqa"),
    ("/facilities-overview", "facilities"),
    ("/records", "records"),
    ("/reports", "reports"),
    ("/trends", "overview"),
    ("/maternal-summary", "overview"),
]


def module_for_path(path: str):
    for frag, mod in PATH_MODULES:
        if frag in path:
            return mod
    return None
