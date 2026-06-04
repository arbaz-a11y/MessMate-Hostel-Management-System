from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def bootstrap_alert_class(tags: str) -> str:
    """
    Map Django message tags ('error', 'success', ...) to Bootstrap alert classes.
    """

    candidates = {t.strip() for t in (tags or "").split() if t.strip()}

    if "error" in candidates or "critical" in candidates:
        return "danger"
    if "warning" in candidates:
        return "warning"
    if "success" in candidates:
        return "success"
    if "debug" in candidates:
        return "secondary"
    if "info" in candidates:
        return "info"

    first = next(iter(sorted(candidates)), "info")
    return first if first in {"primary", "secondary", "success", "danger", "warning", "info"} else "info"


@register.filter
def getattr_safe(obj, attr_name: str):
    """
    Template helper: {{ obj|getattr_safe:"field_name" }}
    """

    if obj is None:
        return ""
    return getattr(obj, attr_name, "")

