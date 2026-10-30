import json
from datetime import date, datetime
from flask import g, has_request_context
from ..extensions import db
from ..models import AuditLog
from ..util import now


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:16]
    if isinstance(v, (list, tuple)):
        return ", ".join(_fmt(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, default=str)[:400]
    return str(v)


def audit(entity, ref, action, old=None, new=None, field=None, label=None):
    """Append one audit entry. Entries are never edited or deleted."""
    from ..security import label as user_label
    u = g.get("user") if has_request_context() else None
    db.session.add(AuditLog(at=now(), user_id=u.id if u else None, user_label=label or (user_label(u) if u else "System"),
                            entity=entity, ref=ref, action=action, field=field,
                            old=_fmt(old)[:2000], new=_fmt(new)[:2000]))


def audit_diff(entity, ref, action, before, after, label=None):
    """One entry per changed field (keys from `after`)."""
    before = before or {}
    changed = 0
    for k, v in after.items():
        if _fmt(before.get(k)) != _fmt(v):
            audit(entity, ref, action, before.get(k), v, k, label)
            changed += 1
    if not changed:
        audit(entity, ref, action, None, None, "(no field changes)", label)
