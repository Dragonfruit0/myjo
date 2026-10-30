from flask import Blueprint, g, request
from sqlalchemy import func, or_
from ..constants import PERMS, ROLE_LABELS, ROLES
from ..extensions import db
from ..models import User
from ..security import (hash_secret, issue_token, login_required, password_problem, pin_problem, screens_for,
                        user_json, verify_login, granted)
from ..services.audit import audit
from ..util import ApiError, req
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__)


def _session(u):
    return {"token": issue_token(u), "user": user_json(u), "must_change": u.must_change}


@bp.post("/auth/login")
def login():
    b = request.get_json(silent=True) or {}
    role = req(b, "role", "Designation", choices=ROLES)
    name = req(b, "username", "Username or email").lower()
    pin = (b.get("pin") or "").strip() or None
    pw = b.get("password")
    if not pin and not pw:
        raise ApiError("Enter your password or PIN.", field="password")
    u = User.query.filter(or_(func.lower(User.username) == name, func.lower(User.email) == name)).first()
    if not u:
        raise ApiError("Username or password is incorrect." if not pin else "Username or PIN is incorrect.", 401)
    if u.role != role:
        raise ApiError(f"This account is not a {ROLE_LABELS[role]} account. Choose {ROLE_LABELS[u.role]} above.")
    verify_login(u, password=pw if not pin else None, pin=pin)
    g.user = u
    audit("Session", u.email, "Signed in", None, f"{u.name} · {ROLE_LABELS[u.role]} · {'PIN' if pin else 'password'}", "session")
    db.session.commit()
    return _session(u)


@bp.post("/auth/setup")
@login_required(allow_setup=True)
def setup():
    u = g.user
    if not u.must_change:
        raise ApiError("Your password and PIN are already set.", 409)
    b = request.get_json(silent=True) or {}
    pw, pin = b.get("password") or "", (b.get("pin") or "").strip()
    if check_password_hash(u.pw_hash, pw):
        raise ApiError("Choose a password different from the temporary one.", field="password")
    e = password_problem(pw)
    if e:
        raise ApiError(e, field="password")
    e = pin_problem(pin)
    if e:
        raise ApiError(e, field="pin")
    u.pw_hash, u.pin_hash, u.must_change = hash_secret(pw), hash_secret(pin), False
    u.token_version += 1
    audit("User", u.email, "Password and PIN set", "temporary", "own password and PIN", "cred")
    db.session.commit()
    return _session(u)


@bp.get("/auth/me")
@login_required(allow_setup=True)
def me():
    u = g.user
    return {"user": user_json(u), "screens": screens_for(u),
            "perms": [c for c, _ in PERMS] if u.role == "admin" else granted(u.role, "action"),
            "must_change": u.must_change}


@bp.post("/auth/change")
@login_required
def change():
    u, b = g.user, request.get_json(silent=True) or {}
    if not check_password_hash(u.pw_hash, b.get("current_password") or ""):
        raise ApiError("Current password is incorrect.", field="current_password")
    npw, npin = b.get("new_password") or "", (b.get("new_pin") or "").strip()
    if not npw and not npin:
        raise ApiError("Enter a new password or a new PIN.")
    if npw:
        e = password_problem(npw)
        if e:
            raise ApiError(e, field="new_password")
        u.pw_hash = hash_secret(npw)
    if npin:
        e = pin_problem(npin)
        if e:
            raise ApiError(e, field="new_pin")
        u.pin_hash = hash_secret(npin)
    what = "Password and PIN" if npw and npin else "Password" if npw else "PIN"
    audit("User", u.email, f"{what} changed", None, "changed", "cred")
    db.session.commit()
    return {"ok": True, "message": f"{what} updated"}


@bp.post("/auth/logout")
@login_required(allow_setup=True)
def logout():
    audit("Session", g.user.email, "Signed out", None, g.user.name, "session")
    db.session.commit()
    return {"ok": True}
