"""Authentication (password / PIN, lockout, JWT) and role-based access checks."""
import re
from datetime import datetime, timedelta, timezone
from functools import wraps
import jwt
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash
from .constants import ROLE_LABELS
from .extensions import db
from .models import Permission, User
from .util import ApiError, now

TRIVIAL_PINS = {"1234", "4321", "0123", "9876", "0000"}


def hash_secret(s):
    return generate_password_hash(s, method=f"pbkdf2:sha256:{current_app.config.get('PASSWORD_ITERATIONS', 600000)}")


def password_problem(p, temp=None):
    if len(p or "") < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", p) or not re.search(r"\d", p):
        return "Password must include letters and numbers."
    if temp and p == temp:
        return "Choose a password different from the temporary one."
    return None


def pin_problem(p):
    if not re.fullmatch(r"\d{4}", p or ""):
        return "PIN must be exactly 4 digits."
    if re.fullmatch(r"(\d)\1{3}", p) or p in TRIVIAL_PINS:
        return "Choose a PIN that is harder to guess."
    return None


def issue_token(user):
    payload = {"sub": str(user.id), "role": user.role, "tv": user.token_version, "mc": user.must_change,
               "exp": datetime.now(timezone.utc) + timedelta(hours=current_app.config["TOKEN_HOURS"])}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def verify_login(user, password=None, pin=None):
    """Check a password or PIN with lockout. Raises ApiError on failure."""
    cfg = current_app.config
    if not user.active:
        raise ApiError("This account is deactivated. Contact Admin.", 403)
    if user.locked_until and user.locked_until > now():
        mins = max(1, int((user.locked_until - now()).total_seconds() // 60) + 1)
        raise ApiError(f"This account is locked. Try again in {mins} minute(s), or ask Admin to unlock it.", 423)
    if pin is not None:
        if not user.pin_hash:
            raise ApiError("No PIN is set for this account. Sign in with your password, then set a PIN under My account.")
        ok = check_password_hash(user.pin_hash, pin)
    else:
        ok = check_password_hash(user.pw_hash, password or "")
    if ok:
        user.failed_attempts = 0
        user.locked_until = None
        return
    from .services.audit import audit
    user.failed_attempts += 1
    if user.failed_attempts >= cfg["MAX_LOGIN_ATTEMPTS"]:
        user.failed_attempts = 0
        user.locked_until = now() + timedelta(minutes=cfg["LOCK_MINUTES"])
        audit("Session", user.email, "Login locked", None, f"{cfg['MAX_LOGIN_ATTEMPTS']} failed attempts", "session", label="System")
        db.session.commit()
        raise ApiError(f"Too many wrong attempts. This account is locked for {cfg['LOCK_MINUTES']} minutes, or Admin can unlock it now.", 423)
    left = cfg["MAX_LOGIN_ATTEMPTS"] - user.failed_attempts
    audit("Session", user.email, "Failed sign-in", None, f"attempt {user.failed_attempts}", "session", label="System")
    db.session.commit()
    raise ApiError(("Wrong PIN. " if pin is not None else "Username or password is incorrect. ") + f"{left} attempt(s) left.", 401)


# ---------- permissions ----------
def granted(role, kind):
    return [p.code for p in Permission.query.filter_by(role=role, kind=kind).all()]


def screens_for(user):
    from .constants import DEFAULT_SCREENS
    if user.role == "admin":
        return DEFAULT_SCREENS["admin"]
    return granted(user.role, "screen")


def can(perm, user=None):
    user = user or g.user
    if user.role == "admin":
        return True
    return db.session.get(Permission, (user.role, "action", perm)) is not None


def has_screen(code, user=None):
    user = user or g.user
    return code in screens_for(user)


def user_json(u):
    from .models import DemoRequest
    school = db.session.get(DemoRequest, u.school_request_id) if u.school_request_id else None
    return {"id": u.id, "username": u.username, "name": u.name, "email": u.email, "phone": u.phone, "role": u.role,
            "role_label": ROLE_LABELS[u.role], "org": u.org, "school_id": u.school_request_id,
            "school_name": school.school.name if school else None}


def label(u=None):
    u = u or g.user
    return f"{u.name} ({ROLE_LABELS[u.role]})"


def login_required(fn=None, *, allow_setup=False):
    def deco(f):
        @wraps(f)
        def inner(*a, **kw):
            hdr = request.headers.get("Authorization", "")
            if not hdr.startswith("Bearer "):
                raise ApiError("Please sign in.", 401)
            try:
                data = jwt.decode(hdr[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                raise ApiError("Your session has expired. Please sign in again.", 401)
            except jwt.InvalidTokenError:
                raise ApiError("Please sign in.", 401)
            user = db.session.get(User, int(data["sub"]))
            if not user or not user.active or user.token_version != data.get("tv"):
                raise ApiError("Please sign in again.", 401)
            if user.must_change and not allow_setup:
                raise ApiError("Set your own password and PIN first.", 403)
            g.user = user
            return f(*a, **kw)
        return inner
    return deco(fn) if fn else deco


def require_perm(*perms):
    for p in perms:
        if can(p):
            return
    raise ApiError("You do not have permission to do this.", 403)


def require_screen(*codes):
    if g.user.role == "admin":
        return
    s = screens_for(g.user)
    if not any(c in s for c in codes):
        raise ApiError("You do not have access to this screen.", 403)


def require_role(*roles):
    if g.user.role not in roles:
        raise ApiError("You do not have access to this.", 403)
