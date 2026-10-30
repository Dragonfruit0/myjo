"""Admin & control: users, access control, masters, cancellations, audit trail, notifications, reminders."""
import re
from datetime import timedelta
from flask import Blueprint, g, request
from sqlalchemy import func, or_
from .. import constants as C
from ..extensions import db
from ..models import (AuditLog, DemoRequest, MarketingFeedback, Notification, Permission, QuestionPaper, Resource, Series,
                      Subject, Training, TrainingHistory, User, DemoFeedback)
from ..security import can, hash_secret, login_required, require_role, require_screen, user_json
from ..services.academic import academic_eligible
from ..services.audit import audit, audit_diff
from ..services.notify import notify, r_school, r_team, r_user
from ..util import ApiError, fmt_dt, human_d, human_dt, now, req, today

bp = Blueprint("admin", __name__)


# ---------------- users ----------------
def admin_user_json(u):
    d = user_json(u)
    d.update(active=u.active, locked=bool(u.locked_until and u.locked_until > now()), temporary=u.must_change)
    return d


@bp.get("/users")
@login_required
def users():
    require_role("admin")
    return {"items": [admin_user_json(u) for u in User.query.order_by(User.role, User.name)]}


def read_user(b, u=None):
    role = u.role if (u and u.role in ("school",)) else req(b, "role", "Role", choices=C.ROLES)
    v = {"name": req(b, "name", "Full name"), "username": req(b, "username", "Username").lower(),
         "email": req(b, "email", "Email", "email"), "phone": req(b, "phone", "Mobile number", "mobile"), "role": role,
         "org": req(b, "org", "Distributor company", required=role == "dist"),
         "school_request_id": req(b, "school_request_id", "School", "int", required=role == "school")}
    if not re.fullmatch(r"[a-z0-9._-]{3,40}", v["username"]):
        raise ApiError("Username must be 3–40 letters, numbers, dots or dashes.", field="username")
    clash = User.query.filter(or_(func.lower(User.username) == v["username"], func.lower(User.email) == v["username"])).first()
    if clash and clash is not u:
        raise ApiError("That username is already taken.", 409, "username")
    clash = User.query.filter(func.lower(User.email) == v["email"]).first()
    if clash and clash is not u:
        raise ApiError("Another user already uses this email.", 409, "email")
    if role == "school":
        r = db.session.get(DemoRequest, v["school_request_id"])
        if not r or not academic_eligible(r):
            raise ApiError("School logins are only for schools with an order.", field="school_request_id")
    else:
        v["school_request_id"] = None
    if role != "dist":
        v["org"] = None
    if u and u.role != role:
        linked = u.id == g.user.id or (u.role == "dist" and DemoRequest.query.filter_by(distributor_id=u.id).count())
        if linked:
            raise ApiError("Role is locked because this login is linked to records.", field="role")
    return v


@bp.post("/users")
@login_required
def add_user():
    require_role("admin")
    b = request.get_json(silent=True) or {}
    v = read_user(b)
    pw, pin = req(b, "temp_password", "Temporary password"), req(b, "temp_pin", "Temporary 4-digit PIN")
    if len(pw) < 8:
        raise ApiError("Temporary password must be at least 8 characters.", field="temp_password")
    if not re.fullmatch(r"\d{4}", pin):
        raise ApiError("PIN must be exactly 4 digits.", field="temp_pin")
    u = User(pw_hash=hash_secret(pw), pin_hash=hash_secret(pin), must_change=True, active=True, **v)
    db.session.add(u)
    db.session.flush()
    audit("User", u.email, "User created", None, f"{u.name} · {C.ROLE_LABELS[u.role]} · username {u.username}", "user")
    db.session.commit()
    return admin_user_json(u), 201


@bp.put("/users/<int:uid>")
@login_required
def edit_user(uid):
    require_role("admin")
    u = db.session.get(User, uid) or _nf("User")
    v = read_user(request.get_json(silent=True) or {}, u)
    before = {k: getattr(u, k) for k in v}
    for k, val in v.items():
        setattr(u, k, val)
    audit_diff("User", u.email, "User edited", before, v)
    db.session.commit()
    return admin_user_json(u)


@bp.post("/users/<int:uid>/toggle")
@login_required
def toggle_user(uid):
    require_role("admin")
    u = db.session.get(User, uid) or _nf("User")
    if u.id == g.user.id:
        raise ApiError("You cannot deactivate yourself.", 409)
    note = ((request.get_json(silent=True) or {}).get("reason") or "").strip()
    audit("User", u.email, "Deactivated" if u.active else "Reactivated", "Active" if u.active else "Inactive",
          ("Inactive" if u.active else "Active") + (f" · {note}" if note else ""), "active")
    u.active = not u.active
    u.token_version += 1
    db.session.commit()
    return admin_user_json(u)


@bp.post("/users/<int:uid>/reset")
@login_required
def reset_user(uid):
    require_role("admin")
    u = db.session.get(User, uid) or _nf("User")
    b = request.get_json(silent=True) or {}
    pw, pin = req(b, "temp_password", "Temporary password"), req(b, "temp_pin", "Temporary 4-digit PIN")
    if len(pw) < 8:
        raise ApiError("Temporary password must be at least 8 characters.", field="temp_password")
    if not re.fullmatch(r"\d{4}", pin):
        raise ApiError("PIN must be exactly 4 digits.", field="temp_pin")
    u.pw_hash, u.pin_hash, u.must_change = hash_secret(pw), hash_secret(pin), True
    u.failed_attempts, u.locked_until = 0, None
    u.token_version += 1
    audit("User", u.email, "Login reset", None, "temporary password and PIN set; unlocked", "cred")
    notify("Portal login reset", [{"name": u.name, "email": u.email, "phone": u.phone}],
           f"Username {u.username} · a temporary password and PIN have been issued by Admin")
    db.session.commit()
    return admin_user_json(u)


def _nf(what):
    raise ApiError(f"{what} not found.", 404)


# ---------------- permissions ----------------
@bp.get("/permissions")
@login_required
def permissions():
    require_role("admin")
    roles = [r for r in C.ROLES]
    granted = {"screens": {r: [] for r in roles}, "actions": {r: [] for r in roles}}
    for p in Permission.query.all():
        granted["screens" if p.kind == "screen" else "actions"].setdefault(p.role, []).append(p.code)
    granted["screens"]["admin"] = C.DEFAULT_SCREENS["admin"]
    granted["actions"]["admin"] = [c for c, _ in C.PERMS]
    return {"roles": [{"code": r, "label": C.ROLE_LABELS[r]} for r in roles],
            "screens": [{"code": c, "label": l, "eligible": {r: C.screen_eligible(r, c) for r in roles}} for c, l in C.SCREENS],
            "actions": [{"code": c, "label": l, "eligible": {r: C.action_eligible(r, c) for r in roles}} for c, l in C.PERMS],
            "granted": granted}


@bp.put("/permissions")
@login_required
def set_permission():
    require_role("admin")
    b = request.get_json(silent=True) or {}
    role, kind, code = req(b, "role", "Role", choices=C.ROLES), req(b, "kind", "Kind", choices=["screen", "action"]), req(b, "code", "Code")
    on = bool(b.get("granted"))
    ok = C.screen_eligible(role, code) if kind == "screen" else C.action_eligible(role, code)
    if not ok:
        raise ApiError("This is not available for that role.", 400)
    p = db.session.get(Permission, (role, kind, code))
    if on and not p:
        db.session.add(Permission(role=role, kind=kind, code=code))
    if not on and p:
        if kind == "screen" and Permission.query.filter_by(role=role, kind="screen").count() <= 1:
            raise ApiError("A role needs at least one screen.", 409)
        db.session.delete(p)
    labels = dict(C.SCREENS if kind == "screen" else C.PERMS)
    audit("Access control", C.ROLE_LABELS[role], ("Screen " if kind == "screen" else "Permission ") + ("granted" if on else "removed"),
          None if on else labels.get(code), labels.get(code) if on else None, kind)
    db.session.commit()
    return permissions()


def reset_permissions():
    Permission.query.delete()
    for role, screens in C.DEFAULT_SCREENS.items():
        if role == "admin":
            continue
        for s in screens:
            db.session.add(Permission(role=role, kind="screen", code=s))
    for code, roles in C.DEFAULT_PERMS.items():
        for role in roles:
            db.session.add(Permission(role=role, kind="action", code=code))


@bp.post("/permissions/reset")
@login_required
def permissions_reset():
    require_role("admin")
    reset_permissions()
    audit("Access control", "All roles", "Restored defaults", "custom", "default", "perms")
    db.session.commit()
    return permissions()


# ---------------- masters ----------------
def series_used(name):
    n = 0
    for r in DemoRequest.query.all():
        n += name in (r.series or []) or bool(r.order and name in r.order.series) or bool(r.dist_order and name in r.dist_order.series)
    n += sum(1 for t in Training.query.all() if name in (t.series or []))
    n += QuestionPaper.query.filter_by(series=name).count() + Resource.query.filter_by(series=name).count()
    return n


def subject_used(name):
    n = 0
    for r in DemoRequest.query.all():
        n += name in (r.subjects or []) or bool(r.order and name in r.order.subjects) or bool(r.dist_order and name in r.dist_order.subjects)
    n += sum(1 for t in Training.query.all() if name in (t.subjects or []))
    n += QuestionPaper.query.filter_by(subject=name).count() + Resource.query.filter_by(subject=name).count()
    return n


def _swap(lst, a, b):
    return [b if x == a else x for x in (lst or [])]


def rename_everywhere(kind, a, b):
    col = "series" if kind == "series" else "subjects"
    for r in DemoRequest.query.all():
        setattr(r, col, _swap(getattr(r, col), a, b))
        for o in (r.order, r.dist_order):
            if o:
                setattr(o, col, _swap(getattr(o, col), a, b))
    for f in DemoFeedback.query.all():
        setattr(f, col, _swap(getattr(f, col), a, b))
    for t in Training.query.all():
        setattr(t, col, _swap(getattr(t, col), a, b))
    single = "series" if kind == "series" else "subject"
    QuestionPaper.query.filter(getattr(QuestionPaper, single) == a).update({single: b})
    Resource.query.filter(getattr(Resource, single) == a).update({single: b})


MODEL = {"series": (Series, series_used, "Book series"), "subjects": (Subject, subject_used, "Subject")}


@bp.get("/masters")
@login_required
def masters():
    require_role("admin")
    return {"series": [{"id": s.id, "name": s.name, "color": s.color, "active": s.active, "used": series_used(s.name)} for s in Series.query.order_by(Series.id)],
            "subjects": [{"id": s.id, "name": s.name, "active": s.active, "used": subject_used(s.name)} for s in Subject.query.order_by(Subject.id)]}


def _master(kind):
    if kind not in MODEL:
        raise ApiError("Unknown list.", 404)
    return MODEL[kind]


@bp.post("/masters/<kind>")
@login_required
def add_master(kind):
    require_role("admin")
    M, _, label = _master(kind)
    b = request.get_json(silent=True) or {}
    name = re.sub(r"\s+", " ", req(b, "name", "Name"))
    if len(name) < 2:
        raise ApiError("Name must be at least 2 characters.", field="name")
    if M.query.filter(func.lower(M.name) == name.lower()).first():
        raise ApiError(f"“{name}” already exists.", 409, "name")
    x = M(name=name, active=True)
    if kind == "series":
        x.color = (b.get("color") or "#4D7C8A")[:9]
    db.session.add(x)
    audit(label, name, "Added", None, name, "name")
    db.session.commit()
    return masters(), 201


@bp.put("/masters/<kind>/<int:xid>")
@login_required
def edit_master(kind, xid):
    require_role("admin")
    M, used, label = _master(kind)
    x = db.session.get(M, xid) or _nf(label)
    b = request.get_json(silent=True) or {}
    name = re.sub(r"\s+", " ", req(b, "name", "Name"))
    if M.query.filter(func.lower(M.name) == name.lower(), M.id != x.id).first():
        raise ApiError(f"“{name}” already exists.", 409, "name")
    if name != x.name:
        n = used(x.name)
        rename_everywhere(kind, x.name, name)
        audit(label, name, "Renamed in records", x.name, f"{name} ({n} records)", "name")
        x.name = name
    if kind == "series" and b.get("color"):
        audit(label, name, "Edited", x.color, b["color"], "color")
        x.color = b["color"][:9]
    db.session.commit()
    return masters()


@bp.post("/masters/<kind>/<int:xid>/toggle")
@login_required
def toggle_master(kind, xid):
    require_role("admin")
    M, _, label = _master(kind)
    x = db.session.get(M, xid) or _nf(label)
    if x.active and M.query.filter_by(active=True).count() < 2:
        raise ApiError(f"Keep at least one active {label.lower()}.", 409)
    x.active = not x.active
    audit(label, x.name, "Activated" if x.active else "Deactivated", "Inactive" if x.active else "Active", "Active" if x.active else "Inactive", "active")
    db.session.commit()
    return masters()


@bp.delete("/masters/<kind>/<int:xid>")
@login_required
def delete_master(kind, xid):
    require_role("admin")
    M, used, label = _master(kind)
    x = db.session.get(M, xid) or _nf(label)
    if used(x.name):
        raise ApiError(f"“{x.name}” is used in records. Deactivate it instead.", 409)
    audit(label, x.name, "Deleted", x.name, None, "name")
    db.session.delete(x)
    db.session.commit()
    return masters()


# ---------------- cancellations ----------------
ENT = {"request": (DemoRequest, "Demo request"), "training": (Training, "Teacher training"),
       "paper": (QuestionPaper, "Question paper"), "resource": (Resource, "Resource")}


def pending_cancellations():
    out = []
    for key, (M, label) in ENT.items():
        for x in M.query.filter(M.cancel_reason.isnot(None), M.cancelled.is_(False)):
            name = x.school.name if key == "request" else (x.title if key in ("training", "resource") else x.request.school.name)
            out.append({"entity": key, "id": x.id, "ref": x.no, "label": label, "name": name, "reason": x.cancel_reason,
                        "by": x.cancel_by, "at": fmt_dt(x.cancel_at)})
    return out


@bp.get("/cancellations")
@login_required
def cancellations():
    if not can("approveCancel"):
        raise ApiError("You do not have permission to approve cancellations.", 403)
    return {"items": pending_cancellations()}


@bp.post("/cancellations/<entity>/<int:xid>/<act>")
@login_required
def decide(entity, xid, act):
    if not can("approveCancel"):
        raise ApiError("You do not have permission to approve cancellations.", 403)
    if entity not in ENT or act not in ("approve", "decline"):
        raise ApiError("Unknown cancellation.", 404)
    M, label = ENT[entity]
    x = db.session.get(M, xid)
    if not x or not x.cancel_pending:
        raise ApiError("No pending cancellation for this record.", 409)
    if act == "approve":
        x.cancelled, x.cancel_approved_by = True, g.user.name
        audit(label, x.no, "Cancellation approved", "active", "cancelled", "cancelled")
        if entity == "training":
            old = x.status
            x.status = "Cancelled"
            db.session.add(TrainingHistory(training_id=x.id, at=now(), by=g.user.name, school="All schools",
                                           action=f"Session cancelled: {x.cancel_reason}"))
            if old == "Scheduled":
                notify("Teacher-training cancelled", [r_school(s.request) for s in x.schools] + [r_user(x.trainer)],
                       f"{x.no} · {x.title} on {human_dt(x.at)} has been cancelled", x.no)
        if entity == "request":
            from ..services.academic import deactivate_school_user
            deactivate_school_user(x, "request cancelled")
    else:
        audit(label, x.no, "Cancellation declined", x.cancel_reason, None, "cancel")
        x.cancel_reason = x.cancel_by = x.cancel_at = None
    db.session.commit()
    return {"items": pending_cancellations()}


# ---------------- audit & notifications ----------------
@bp.get("/audit")
@login_required
def audit_list():
    require_screen("audit")
    q = AuditLog.query
    if request.args.get("entity"):
        q = q.filter(AuditLog.entity == request.args["entity"])
    t = (request.args.get("q") or "").strip()
    if t:
        like = f"%{t}%"
        q = q.filter(or_(AuditLog.ref.like(like), AuditLog.user_label.like(like), AuditLog.action.like(like),
                         AuditLog.field.like(like), AuditLog.old.like(like), AuditLog.new.like(like)))
    n = min(int(request.args.get("limit", 300)), 1000)
    rows = q.order_by(AuditLog.id.desc()).limit(n).all()
    return {"items": [{"at": a.at.strftime("%Y-%m-%d %H:%M:%S"), "user": a.user_label, "entity": a.entity, "ref": a.ref,
                       "action": a.action, "field": a.field, "old": a.old, "new": a.new} for a in rows],
            "entities": [e for (e,) in db.session.query(AuditLog.entity).distinct().order_by(AuditLog.entity)]}


@bp.get("/notifications")
@login_required
def notifications():
    require_screen("notifications")
    n = min(int(request.args.get("limit", 150)), 500)
    rows = Notification.query.order_by(Notification.id.desc()).limit(n).all()
    return {"items": [{"at": fmt_dt(x.at), "event": x.event, "message": x.message, "ref": x.ref, "recipients": x.recipients,
                       "channel": x.channel, "status": x.status} for x in rows]}


def run_reminders():
    """Demo/training reminders (within 48 h, once) and overdue reminders (once a day). Safe to run from cron."""
    sent, nl, lim, td = 0, now(), now() + timedelta(hours=48), today()
    for r in DemoRequest.query.filter_by(status="Demo Scheduled", cancelled=False):
        s = r.schedule
        if s and not s.reminded and nl <= s.at <= lim:
            notify("Demo reminder", [r_school(r), {"name": r.distributor.org, "email": r.distributor.email, "phone": r.distributor.phone},
                                     r_user(s.presenter), r_user(s.marketing)],
                   f"{r.school.name} demo on {human_dt(s.at)}" + (f" · {s.link}" if s.link else ""), r.no)
            s.reminded, sent = True, sent + 1
    for m in MarketingFeedback.query.filter(MarketingFeedback.next_follow.isnot(None)):
        r = db.session.get(DemoRequest, m.request_id)
        if r.cancelled or r.status in ("Converted", "Not Converted", "Rejected") or m.next_follow > td or m.reminded_on == td:
            continue
        notify("Overdue task reminder" if m.next_follow < td else "Follow-up due reminder", [r_user(m.person)],
               f"{r.school.name} · {m.next_action or 'Follow up'} · due {human_d(m.next_follow)}", r.no)
        m.reminded_on, sent = td, sent + 1
    for t in Training.query.filter_by(status="Scheduled", cancelled=False):
        if not t.reminded and nl <= t.at <= lim:
            notify("Teacher-training reminder", [r_school(s.request) for s in t.schools if s.school_confirm != "Declined"] + [r_user(t.trainer)],
                   f"{t.no} · {t.title} · {human_dt(t.at)} · {t.link or t.venue}", t.no)
            t.reminded, sent = True, sent + 1
        if t.at < nl and t.reminded_on != td:
            notify("Overdue task reminder", [r_user(t.trainer) or r_team("acad", "Academic Support Team")],
                   f"{t.no} · {t.title} · completion not recorded since {human_dt(t.at)}", t.no)
            t.reminded_on, sent = td, sent + 1
    for p in QuestionPaper.query.filter(QuestionPaper.cancelled.is_(False), QuestionPaper.due_date < td,
                                        QuestionPaper.status.notin_(list(C.PAPER_LIVE) + ["Closed"])):
        if p.reminded_on != td:
            notify("Overdue task reminder", [r_user(p.assignee) if p.assignee else r_team("acad", "Academic Support Team")],
                   f"{p.no} · {p.request.school.name} · due {human_d(p.due_date)}", p.no)
            p.reminded_on, sent = td, sent + 1
    return sent


@bp.post("/reminders/run")
@login_required
def reminders():
    require_screen("notifications", "dashboard")
    if g.user.role in ("dist", "school"):
        raise ApiError("Not allowed.", 403)
    n = run_reminders()
    db.session.commit()
    return {"sent": n}
