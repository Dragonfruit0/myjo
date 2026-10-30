"""Small shared helpers: time, errors, validation, number sequences, formatting."""
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from flask import current_app, jsonify
from .extensions import db
from .models import Sequence


class ApiError(Exception):
    def __init__(self, message, status=400, field=None):
        super().__init__(message)
        self.message, self.status, self.field = message, status, field

    def response(self):
        body = {"error": self.message}
        if self.field:
            body["field"] = self.field
        return jsonify(body), self.status


def now():
    """Current local time (naive), in the configured business time zone."""
    return datetime.now(ZoneInfo(current_app.config["TIMEZONE"])).replace(tzinfo=None, second=0, microsecond=0)


def today():
    return now().date()


def fmt_d(d):
    return d.isoformat() if d else None


def fmt_dt(d):
    return d.strftime("%Y-%m-%dT%H:%M") if d else None


def human_d(d):
    return d.strftime("%d %b %Y") if d else "—"


def human_dt(d):
    return d.strftime("%d %b %Y, %I:%M %p") if d else "—"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


# ---------- validation ----------
def req(body, key, label, kind="text", required=True, choices=None):
    """Read one field from a JSON body, validate it and return the clean value."""
    v = body.get(key) if isinstance(body, dict) else None
    if isinstance(v, str):
        v = v.strip()
    empty = v is None or v == "" or (isinstance(v, list) and not v)
    if empty:
        if required:
            raise ApiError(f"{label} is required.", field=key)
        return [] if kind == "list" else None
    if kind == "int":
        try:
            f = float(v)
        except (TypeError, ValueError):
            raise ApiError(f"{label} must be a number.", field=key)
        if f != int(f):
            raise ApiError(f"{label} must be a whole number.", field=key)
        v = int(f)
        if v < 0:
            raise ApiError(f"{label} cannot be negative.", field=key)
    elif kind == "date":
        try:
            v = date.fromisoformat(str(v)[:10])
        except ValueError:
            raise ApiError(f"{label} must be a valid date.", field=key)
    elif kind == "datetime":
        try:
            v = datetime.fromisoformat(str(v)[:16])
        except ValueError:
            raise ApiError(f"{label} must be a valid date and time.", field=key)
    elif kind == "email":
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", v):
            raise ApiError(f"{label} must be a valid email address.", field=key)
        v = v.lower()
    elif kind == "mobile":
        digits = re.sub(r"[\s-]", "", str(v))
        if not re.fullmatch(r"(\+?91)?[6-9]\d{9}", digits):
            raise ApiError(f"{label} must be a 10-digit Indian mobile number.", field=key)
        v = digits[-10:]
    elif kind == "pincode":
        if not re.fullmatch(r"\d{6}", str(v)):
            raise ApiError(f"{label} must be 6 digits.", field=key)
    elif kind == "url":
        if not re.fullmatch(r"https?://\S+", v):
            raise ApiError(f"{label} must start with https://", field=key)
    elif kind == "list":
        if not isinstance(v, list):
            raise ApiError(f"{label} must be a list.", field=key)
        v = [str(x).strip() for x in v if str(x).strip()]
        if choices is not None:
            bad = [x for x in v if x not in choices]
            if bad:
                raise ApiError(f"{label}: '{bad[0]}' is not a valid choice.", field=key)
        return v
    elif kind == "text":
        v = str(v)
    if choices is not None and v not in choices:
        raise ApiError(f"{label}: '{v}' is not a valid choice.", field=key)
    return v


def next_no(name, prefix, width=4):
    """Atomic per-name counter (row lock on MySQL)."""
    seq = db.session.get(Sequence, name, with_for_update=True)
    if not seq:
        seq = Sequence(name=name, value=0)
        db.session.add(seq)
    seq.value += 1
    db.session.flush()
    return f"{prefix}{str(seq.value).zfill(width)}"


def days_between(a, b):
    return (b - a).days


def add_days(d, n):
    return d + timedelta(days=n)
