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
