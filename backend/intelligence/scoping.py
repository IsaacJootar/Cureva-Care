"""Server-side scope resolution (cureva-docs/04 "Tenant scoping is read, never
assumed", 07).

A Facility lead is scoped to their one facility; an Organisation user to their
organisation's EFFECTIVE facility set — the union of every explicit and
region-level grant, resolved here on every request, never trusted from the
client. The access tier is capped at whatever the organisation's grant allows.
"""
from identity_access.models import (
    AccessLevel,
    Facility,
    OrganisationFacilityAccess,
    Role,
    ScopeType,
)

_TIER_ORDER = {AccessLevel.AGGREGATE: 0, AccessLevel.DE_IDENTIFIED: 1, AccessLevel.IDENTIFIABLE: 2}


def resolve_org_facility_ids(organisation_id) -> set:
    """Every facility id an organisation can view, expanding region grants."""
    facility_ids: set = set()
    grants = OrganisationFacilityAccess.objects.filter(organisation_id=organisation_id)
    for g in grants:
        if g.scope_type == ScopeType.FACILITY:
            facility_ids.add(g.scope_id)
        elif g.scope_type == ScopeType.WARD:
            facility_ids.update(Facility.objects.filter(ward_id=g.scope_id).values_list("id", flat=True))
        elif g.scope_type == ScopeType.LOCAL_GOVERNMENT:
            facility_ids.update(
                Facility.objects.filter(ward__local_government_id=g.scope_id).values_list("id", flat=True)
            )
        elif g.scope_type == ScopeType.STATE:
            facility_ids.update(
                Facility.objects.filter(ward__local_government__state_id=g.scope_id).values_list("id", flat=True)
            )
    return facility_ids


def resolve_org_access_level(organisation_id) -> str:
    """The highest tier any of the organisation's grants allows (each grant can
    differ; the cap is the max). Defaults to the least-identifiable tier."""
    grants = OrganisationFacilityAccess.objects.filter(organisation_id=organisation_id)
    best = AccessLevel.AGGREGATE
    for g in grants:
        if _TIER_ORDER[g.access_level] > _TIER_ORDER[best]:
            best = g.access_level
    return best


def resolve_scope(user, request) -> dict:
    """caller_scope, optionally narrowed by a ?facility= or ?state= filter from
    the dashboard scope selector. The filter can only INTERSECT the caller's
    allowed facilities — it can never widen access (07-security). Returns the
    same shape as caller_scope."""
    scope = caller_scope(user)
    allowed = scope["facility_ids"]
    if allowed is None:
        return scope
    ids = set(allowed)
    facility = request.query_params.get("facility")
    state = request.query_params.get("state")
    if facility:
        ids = {f for f in ids if str(f) == str(facility)}
    elif state:
        ids = set(
            Facility.objects.filter(id__in=ids, ward__local_government__state_id=state)
            .values_list("id", flat=True)
        )
    return {"facility_ids": ids, "access_level": scope["access_level"]}


def scope_options(user) -> dict:
    """The facilities (and the distinct states they fall in) that the caller may
    view — powers the dashboard scope selector."""
    scope = caller_scope(user)
    allowed = scope["facility_ids"]
    if not allowed:
        return {"facilities": [], "states": []}
    facs = (
        Facility.objects.filter(id__in=allowed)
        .select_related("ward__local_government__state")
        .order_by("ward__local_government__state__name", "name")
    )
    facilities, states, seen = [], [], set()
    for f in facs:
        st = f.ward.local_government.state
        facilities.append({"id": str(f.id), "name": f.name, "state": st.name, "state_id": str(st.id)})
        if st.id not in seen:
            seen.add(st.id)
            states.append({"id": str(st.id), "name": st.name})
    return {"facilities": facilities, "states": states}


def caller_scope(user) -> dict:
    """Returns {'facility_ids': set|None, 'access_level': str}. facility_ids is
    None for a caller with no dashboard scope (e.g. a Systems admin)."""
    if user.role == Role.FACILITY_LEAD and user.facility_id:
        return {"facility_ids": {user.facility_id}, "access_level": AccessLevel.IDENTIFIABLE}
    if user.role == Role.ORGANISATION_USER and user.organisation_id:
        return {
            "facility_ids": resolve_org_facility_ids(user.organisation_id),
            "access_level": resolve_org_access_level(user.organisation_id),
        }
    return {"facility_ids": None, "access_level": AccessLevel.AGGREGATE}
