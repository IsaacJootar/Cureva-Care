"""The single shared accessor for platform settings and notification channels.

Every other module reads a tunable value through get_setting() — never the
PlatformSetting table directly, and never a local constant. Values are cached
with a short TTL and the cache entry is invalidated on write, so a change from
/admin/settings takes effect within seconds, not after a redeploy
(cureva-docs/04-architecture-and-stack.md).
"""
from decimal import Decimal, InvalidOperation

from django.core.cache import cache

from .settings_registry import DEFAULTS_BY_KEY

_CACHE_PREFIX = "platform_setting:"
_CACHE_TTL_SECONDS = 20


def _cache_key(key):
    return f"{_CACHE_PREFIX}{key}"


def _coerce(value, value_type):
    """Coerce a stored JSON value into its declared Python type."""
    if value_type == "integer":
        return int(value)
    if value_type == "decimal":
        return float(value)
    if value_type == "boolean":
        return bool(value)
    return str(value)


def get_setting(key):
    """Return the current typed value for a platform setting.

    Falls back to the registry default if the row has not been seeded yet, so
    the system is operational before an admin ever visits the settings screen.
    """
    cached = cache.get(_cache_key(key))
    if cached is not None:
        return cached

    # Imported lazily to avoid an app-loading cycle at import time.
    from .models import PlatformSetting

    try:
        row = PlatformSetting.objects.get(pk=key)
        value = _coerce(row.value, row.value_type)
    except PlatformSetting.DoesNotExist:
        definition = DEFAULTS_BY_KEY.get(key)
        if definition is None:
            raise KeyError(f"Unknown platform setting: {key!r}")
        value = _coerce(definition["value"], definition["value_type"])

    cache.set(_cache_key(key), value, _CACHE_TTL_SECONDS)
    return value


def invalidate_setting(key):
    cache.delete(_cache_key(key))


class SettingValidationError(ValueError):
    pass


def validate_value(raw, value_type):
    """Validate/normalise an incoming value against its declared type.

    Returns the JSON-serialisable value to store. Raises
    SettingValidationError on a bad value.
    """
    if value_type == "integer":
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise SettingValidationError("Value must be an integer.")
    if value_type == "decimal":
        try:
            return float(Decimal(str(raw)))
        except (InvalidOperation, TypeError, ValueError):
            raise SettingValidationError("Value must be a decimal number.")
    if value_type == "boolean":
        if isinstance(raw, bool):
            return raw
        if str(raw).lower() in {"true", "1", "yes"}:
            return True
        if str(raw).lower() in {"false", "0", "no"}:
            return False
        raise SettingValidationError("Value must be a boolean.")
    # string
    return str(raw)


def set_setting(key, raw_value, updated_by=None):
    """Update one platform setting's value, validated against its declared
    type, and invalidate the cache. Returns the updated row."""
    from .models import PlatformSetting

    row = PlatformSetting.objects.get(pk=key)
    row.value = validate_value(raw_value, row.value_type)
    row.updated_by = updated_by
    row.save(update_fields=["value", "updated_by", "updated_at"])
    invalidate_setting(key)
    return row
