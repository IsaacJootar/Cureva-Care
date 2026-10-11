"""Template resolution and source fingerprinting.

Resolution prefers a facility-specific active template, falling back to the
shared/default (facility IS NULL) for that register family — so a facility
whose form differs never breaks intake, and most facilities use the default
(cureva-docs/03-templates-and-intake.md).
"""
import hashlib

from .models import Template


class NoTemplateRegistered(Exception):
    def __init__(self, register_family, facility_id):
        super().__init__(
            f"No active template for register_family={register_family!r} "
            f"(facility={facility_id})"
        )


def resolve_template(register_family: str, facility_id):
    """Facility-specific active template first, then the shared default.
    Returns the Template instance, or raises NoTemplateRegistered."""
    template = (
        Template.objects.filter(
            register_family=register_family, facility_id=facility_id, is_active=True
        )
        .order_by("-version")
        .first()
    )
    if template is None:
        template = (
            Template.objects.filter(
                register_family=register_family, facility__isnull=True, is_active=True
            )
            .order_by("-version")
            .first()
        )
    if template is None:
        raise NoTemplateRegistered(register_family, facility_id)
    return template


def shared_templates_by_family() -> dict:
    """The active shared/default template for each family — enough for the
    register-family cross-check."""
    out = {}
    for family in ("ANC", "Delivery", "PNC"):
        t = (
            Template.objects.filter(
                register_family=family, facility__isnull=True, is_active=True
            )
            .order_by("-version")
            .first()
        )
        if t is not None:
            out[family] = t.schema
    return out


def compute_source_hash(page_bytes: list[bytes]) -> str:
    """Combined checksum over all page images in a batch. Order-independent so a
    re-upload of the same pages in any order is still detected as a duplicate."""
    per_page = sorted(hashlib.sha256(b).hexdigest() for b in page_bytes)
    combined = hashlib.sha256("".join(per_page).encode("utf-8")).hexdigest()
    return combined


def compute_page_hash(page: bytes) -> str:
    return hashlib.sha256(page).hexdigest()
