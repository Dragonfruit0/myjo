"""Demo requests: the school pipeline from request to order (Myjo and distributor order paths)."""
from flask import Blueprint, g, request
from sqlalchemy import func, or_
from .. import constants as C
from ..extensions import db
from ..models import (Attachment, AuditLog, DemoFeedback, DemoRequest, DemoSchedule, DistOrder, FollowUp,
                      MarketingFeedback, QuestionPaper, School, User)
from ..security import can, login_required, require_perm
from ..services.academic import (academic_eligible, active_series, active_subjects, convert, coverage, create_pack,
                                 deactivate_school_user, ensure_school_user, pack_summary, read_order, read_pack,
                                 set_order, set_status, trainings_for, visible_resources_for)
from ..services.audit import audit, audit_diff
from ..services.notify import notify, r_dist, r_school, r_team, r_user
from ..util import ApiError, fmt_d, fmt_dt, human_d, human_dt, next_no, now, req, today
from .files import file_json

bp = Blueprint("requests", __name__)
FINAL = ("Converted", "Not Converted", "Rejected")
OPEN_REVIEW = ("New", "Under Review", "On Hold")
MKT_STAGE = ("Demo Completed", "Follow-up Pending", "Converted", "Not Converted")


# ---------- access ----------
def visible_query():
    q = DemoRequest.query
    if g.user.role == "dist":
        q = q.filter(DemoRequest.distributor_id == g.user.id)
    elif g.user.role == "school":
        q = q.filter(DemoRequest.id == -1)
    return q


def get_request(rid):
    r = visible_query().filter(DemoRequest.id == rid).first()
    if not r:
        raise ApiError("Request not found or not visible to you.", 404)
    return r


def is_final(r):
    return r.status in FINAL or r.cancelled


def can_dist_order(r):
    return (not r.cancelled and r.status not in ("Converted", "Rejected")
            and (not r.dist_order or r.dist_order.status in ("Returned", "Rejected")))


def actions_for(r):
    a, role = [], g.user.role
    if r.cancelled:
        return a
    if can("editRequest") and r.status in OPEN_REVIEW and (role != "dist" or r.distributor_id == g.user.id):
        a.append("edit")
    if can("review"):
        if r.status == "New":
            a.append("review")
        if r.status in OPEN_REVIEW:
            a += ["approve", "info", "reject"]
        if r.status in ("New", "Under Review"):
            a.append("hold")
        if r.status == "On Hold":
            a.append("resume")
        if not is_final(r):
            a.append("assign")
    if can("schedule") and r.status in ("Approved", "Demo Scheduled"):
        a.append("schedule")
    if can("schedule") and r.status == "Demo Scheduled":
        a.append("share")
    if can("feedback") and (r.status == "Demo Scheduled" or (r.feedback and r.status in MKT_STAGE)):
        a.append("feedback")
    if can("marketing") and r.status in MKT_STAGE:
        a += ["marketing", "followup"]
    if can("order") and (r.status in MKT_STAGE or r.direct):
        a.append("order")
    d = r.dist_order
    if role == "dist":
        if can("placeOrder") and can_dist_order(r):
            a.append("dist_order")
        if can("directConfirm") and d and d.status == "Submitted":
            a.append("dist_confirm")
        if can("directConfirm") and d and d.direct and r.status == "Converted":
            a.append("dist_update")
    if can("order") and d and d.status == "Submitted":
        a += ["accept_dist", "return_dist", "reject_dist"]
    if (can("review") or can("order")) and not r.cancel_pending:
        a.append("cancel")
    return a


# ---------- serialisers ----------
def school_json(s, full=False):
    d = {"id": s.id, "name": s.name, "city": s.city, "state": s.state, "board": s.board}
    if full:
        d.update(address=s.address, pincode=s.pincode, strength=s.strength, contact=s.contact,
                 designation=s.designation, mobile=s.mobile, email=s.email)
    return d


def dist_json(u):
    return {"id": u.id, "name": u.org or u.name, "phone": u.phone}


def list_json(r):
    return {"id": r.id, "no": r.no, "created_at": fmt_dt(r.created_at), "ay": r.ay, "status": r.status,
            "order_status": r.order_status, "school": school_json(r.school), "distributor": dist_json(r.distributor),
            "assigned_to": r.assigned_to, "pref_date": fmt_d(r.pref_date), "pref_time": r.pref_time,
            "cancelled": r.cancelled, "cancel_pending": r.cancel_pending, "direct": r.direct}


def files_of(entity, eid):
    return [file_json(a.file) for a in Attachment.query.filter_by(entity=entity, entity_id=eid)]


def order_json(o):
    return {"ay": o.ay, "po": o.po, "series": o.series, "classes": o.classes, "subjects": o.subjects, "qty": o.qty,
            "conf_date": fmt_d(o.conf_date), "del_date": fmt_d(o.del_date), "payment": o.payment,
            "remarks": o.remarks, "source": o.source} if o else None


def dist_order_json(d):
    if not d:
        return None
    return {"status": d.status, "direct": d.direct, "ay": d.ay, "po": d.po, "series": d.series, "classes": d.classes,
            "subjects": d.subjects, "qty": d.qty, "req_delivery": fmt_d(d.req_delivery), "remarks": d.remarks,
            "files": files_of("dist_order", d.request_id), "by": d.by, "at": fmt_dt(d.at), "review_note": d.review_note,
            "reviewed_by": d.reviewed_by, "reviewed_at": fmt_dt(d.reviewed_at)}


def steps(r):
    any_ac = bool(trainings_for(r.id)) or QuestionPaper.query.filter_by(request_id=r.id).count() > 0
    return [{"label": l, "done": bool(d), "stopped": bool(x)} for l, d, x in [
        ("Request", True, False),
        ("Approved", r.status not in OPEN_REVIEW + ("Rejected",), r.status == "Rejected"),
        ("Scheduled", r.schedule, False),
        ("Link / details shared", r.schedule and r.schedule.shared_at, False),
        ("Myjo feedback", r.feedback, False),
        ("Marketing follow-up", r.marketing or r.followups, r.status == "Not Converted"),
        ("Order converted", r.status == "Converted", False),
        ("Academic support", any_ac, False)]]


def detail_json(r):
    internal = g.user.role not in ("dist", "school")
    s, f, m = r.schedule, r.feedback, r.marketing
    d = list_json(r)
    d.update({
        "remarks": r.remarks, "classes": r.classes, "subjects": r.subjects, "series": r.series, "exp_qty": r.exp_qty,
        "school": school_json(r.school, True),
        "notes": [{"at": fmt_dt(n.at), "by": n.by, "type": n.type, "text": n.text} for n in r.notes],
        "schedule": {"at": fmt_dt(s.at), "mode": s.mode, "presenter": s.presenter, "marketing": s.marketing,
                     "platform": s.platform, "link": s.link, "venue": s.venue, "agenda": s.agenda,
                     "instructions": s.instructions, "shared_at": fmt_dt(s.shared_at), "reminded": s.reminded} if s else None,
        "feedback": {"by": f.by, "date": fmt_d(f.date), "attendees": f.attendees, "designations": f.designations,
                     "classes": f.classes, "subjects": f.subjects, "series": f.series, "interest": f.interest,
                     "requirements": f.requirements, "requested": f.requested, "objections": f.objections,
                     "competitor": f.competitor, "next_follow": fmt_d(f.next_follow), "remarks": f.remarks,
                     "files": files_of("feedback", r.id)} if (f and internal) else None,
        "marketing": {"potential": m.potential, "dm_name": m.dm_name, "dm_desig": m.dm_desig, "dm_mobile": m.dm_mobile,
                      "dm_email": m.dm_email, "competitor": m.competitor, "exp_qty": m.exp_qty,
                      "decision_date": fmt_d(m.decision_date), "stage": m.stage, "remarks": m.remarks,
                      "next_action": m.next_action, "next_follow": fmt_d(m.next_follow), "person": m.person,
                      "overdue": bool(m.next_follow and m.next_follow < today() and not is_final(r))} if (m and internal) else None,
        "followups": [{"id": x.id, "at": fmt_dt(x.at), "method": x.method, "person": x.person, "summary": x.summary,
                       "next_action": x.next_action, "next_date": fmt_d(x.next_date), "by": x.by} for x in r.followups] if internal else [],
        "order": order_json(r.order), "dist_order": dist_order_json(r.dist_order),
        "cancel": {"reason": r.cancel_reason, "by": r.cancel_by, "at": fmt_dt(r.cancel_at), "approved_by": r.cancel_approved_by} if r.cancel_reason else None,
        "steps": steps(r), "actions": actions_for(r),
    })
    elig = academic_eligible(r)
    if elig or r.pack:
        login = User.query.filter_by(school_request_id=r.id).first()
        d["academic"] = {
            "eligible": elig, "coverage": coverage(r),
            "trainings": [{"id": t.id, "no": t.no, "title": t.title, "status": t.status, "at": fmt_dt(t.at)} for t in trainings_for(r.id)],
            "papers": [{"id": p.id, "no": p.no, "status": p.status, "cls": p.cls, "subject": p.subject, "exam": p.exam}
                       for p in QuestionPaper.query.filter_by(request_id=r.id, cancelled=False).order_by(QuestionPaper.id)],
            "resources_count": len(visible_resources_for(r)),
            "pack": {"at": fmt_dt(r.pack.at), "by": r.pack.by, "training_id": r.pack.training_id,
                     "paper_ids": r.pack.paper_ids, "resource_ids": r.pack.resource_ids} if r.pack else None,
            "login": {"username": login.username, "active": login.active} if login and internal else None,
        }
    else:
        d["academic"] = None
    if can("seeInternal"):
        d["audit"] = [{"at": fmt_dt(a.at), "user": a.user_label, "action": a.action, "field": a.field, "old": a.old, "new": a.new}
                      for a in AuditLog.query.filter_by(ref=r.no).order_by(AuditLog.id.desc()).limit(60)]
    return d


# ---------- list / create / edit ----------
@bp.get("/requests")
@login_required
def list_requests():
    if g.user.role == "school":
        raise ApiError("Not available for school users.", 403)
    q = visible_query().join(School, DemoRequest.school_id == School.id)
    if request.args.get("status"):
        q = q.filter(DemoRequest.status == request.args["status"])
    t = (request.args.get("q") or "").strip().lower()
    if t:
        like = f"%{t}%"
        q = q.filter(or_(func.lower(DemoRequest.no).like(like), func.lower(School.name).like(like),
                         func.lower(School.city).like(like), func.lower(School.state).like(like),
                         School.mobile.like(like), func.lower(School.contact).like(like)))
    rows = q.order_by(DemoRequest.created_at.desc()).all()
    return {"items": [list_json(r) for r in rows], "total": len(rows)}


def read_school(b, key="school"):
    s = b.get(key) or {}
    return {
        "name": req(s, "name", "School name"), "address": req(s, "address", "School address"),
        "city": req(s, "city", "City"), "state": req(s, "state", "State"),
        "pincode": req(s, "pincode", "Pincode", "pincode"), "board": req(s, "board", "School board", choices=C.BOARDS),
        "strength": req(s, "strength", "Student strength", "int", required=False),
        "contact": req(s, "contact", "Contact person name"), "designation": req(s, "designation", "Designation"),
        "mobile": req(s, "mobile", "Mobile number", "mobile"), "email": req(s, "email", "Email address", "email"),
    }


def read_request_fields(b, creating):
    out = {
        "ay": req(b, "ay", "Academic year", choices=C.ACADEMIC_YEARS),
        "classes": req(b, "classes", "Classes / grades required", "list", choices=C.CLASSES),
        "subjects": req(b, "subjects", "Subjects required", "list", choices=active_subjects()),
        "series": req(b, "series", "Myjo book series of interest", "list", choices=active_series()),
        "exp_qty": req(b, "exp_qty", "Expected order quantity", "int", required=False),
        "pref_date": req(b, "pref_date", "Preferred demo date", "date"),
        "pref_time": req(b, "pref_time", "Preferred demo time"),
        "remarks": req(b, "remarks", "Remarks", required=False),
    }
    if creating and out["pref_date"] < today():
        raise ApiError("Preferred demo date cannot be in the past.", field="pref_date")
    return out


def pick_distributor(b):
    if g.user.role == "dist":
        return g.user
    did = req(b, "distributor_id", "Distributor", "int")
    d = db.session.get(User, did)
    if not d or d.role != "dist" or not d.active:
        raise ApiError("Choose an active distributor.", field="distributor_id")
    return d


def check_duplicate(name, city, ay, exclude=None):
    q = (DemoRequest.query.join(School).filter(func.lower(School.name) == name.lower(), func.lower(School.city) == city.lower(),
                                               DemoRequest.ay == ay, DemoRequest.cancelled.is_(False),
                                               DemoRequest.status.notin_(["Rejected", "Not Converted"])))
    if exclude:
        q = q.filter(DemoRequest.id != exclude)
    dup = q.first()
    if dup:
        raise ApiError(f"An active request already exists for this school and academic year ({dup.no}).", 409, "school.name")


def new_request(school, fields, dist, status="New", direct=False, remarks=None):
    s = School(distributor_id=dist.id, created_at=now(), **school)
    db.session.add(s)
    db.session.flush()
    r = DemoRequest(no=next_no("request", f"MYJO-DR-{today().year}-"), school_id=s.id, distributor_id=dist.id,
                    status=status, direct=direct, created_at=now(), created_by=g.user.id, **fields)
    if remarks:
        r.remarks = remarks
    db.session.add(r)
    db.session.flush()
    return r


@bp.post("/requests")
@login_required
def create_request():
    require_perm("createRequest")
    b = request.get_json(silent=True) or {}
    school, fields, dist = read_school(b), read_request_fields(b, True), pick_distributor(b)
    check_duplicate(school["name"], school["city"], fields["ay"])
    r = new_request(school, fields, dist)
    audit("Demo request", r.no, "Created", None, "New", "status")
    notify("New demo request submitted", [r_team("demo", "Myjo Demo Team"), r_dist(r)], f"{r.no} · {r.school.name}, {r.school.city}", r.no)
    db.session.commit()
    return detail_json(r), 201


@bp.get("/requests/<int:rid>")
@login_required
def get_one(rid):
    return detail_json(get_request(rid))


def need(r, action):
    if action not in actions_for(r):
        raise ApiError("This action is not available for this request right now.", 409)


@bp.put("/requests/<int:rid>")
@login_required
def edit_request(rid):
    r = get_request(rid)
    need(r, "edit")
    b = request.get_json(silent=True) or {}
    school, fields = read_school(b), read_request_fields(b, False)
    check_duplicate(school["name"], school["city"], fields["ay"], exclude=r.id)
    before = {**{k: getattr(r.school, k) for k in school}, **{k: getattr(r, k) for k in fields}}
    for k, v in school.items():
        setattr(r.school, k, v)
    for k, v in fields.items():
        setattr(r, k, v)
    if g.user.role != "dist" and b.get("distributor_id"):
        d = pick_distributor(b)
        r.distributor_id = r.school.distributor_id = d.id
    audit_diff("Demo request", r.no, "Edited", before, {**school, **fields})
    db.session.commit()
    return detail_json(r)


# ---------- review ----------
def reason(b, label="Reason"):
    return req(b, "reason", label)


@bp.post("/requests/<int:rid>/<string:act>")
@login_required
def review_action(rid, act):
    if act not in ("review", "approve", "reject", "info", "hold", "resume", "assign", "share", "cancel"):
        raise ApiError("Unknown action.", 404)
    r = get_request(rid)
    need(r, act)
    b = request.get_json(silent=True) or {}
    out = {}
    if act == "review":
        set_status(r, "Under Review", "Review started")
        if not r.assigned_to:
            audit("Demo request", r.no, "Assigned", None, g.user.name, "assigned_to")
            r.assigned_to = g.user.name
    elif act == "approve":
        note = (b.get("note") or "").strip() or None
        set_status(r, "Approved", "Approved", note)
        notify("Demo approved", [r_school(r), r_dist(r)], f"{r.no} · {r.school.name} approved. Demo schedule will follow." + (f" {note}" if note else ""), r.no)
    elif act == "reject":
        t = reason(b)
        set_status(r, "Rejected", "Rejected", t)
        notify("Demo rejected", [r_school(r), r_dist(r)], f"{r.no} · {r.school.name} · {t}", r.no)
    elif act == "info":
        t = reason(b, "What you need")
        set_status(r, "Under Review", "More information requested", t)
        notify("More information requested", [r_dist(r), r_school(r)], f"{r.no} · {t}", r.no)
    elif act == "hold":
        t = reason(b)
        set_status(r, "On Hold", "Put on hold", t)
        notify("Demo put on hold", [r_school(r), r_dist(r)], f"{r.no} · {t}", r.no)
    elif act == "resume":
        set_status(r, "Under Review", "Review resumed")
    elif act == "assign":
        who = req(b, "assigned_to", "Myjo team member")
        if not User.query.filter_by(name=who, role="demo", active=True).first():
            raise ApiError("Choose an active Demo Team member.", field="assigned_to")
        audit("Demo request", r.no, "Assigned", r.assigned_to, who, "assigned_to")
        r.assigned_to = who
        notify("Demo request assigned", [r_user(who)], f"{r.no} · {r.school.name}", r.no)
    elif act == "share":
        s = r.schedule
        msg = (f"Myjo Publications · Demo confirmation\nRequest: {r.no}\nSchool: {r.school.name}, {r.school.city}\n"
               f"Date & time: {human_dt(s.at)}\nMode: {s.mode}{' (' + s.platform + ')' if s.platform else ''}\n"
               + (f"Join link: {s.link}\n" if s.mode == "Online" else f"Venue: {s.venue}\n")
               + f"Presenter: {s.presenter}\nMarketing contact: {s.marketing}\nAgenda: {s.agenda or '—'}\n"
               + (f"Instructions: {s.instructions}\n" if s.instructions else "")
               + f"Distributor: {r.distributor.org} ({r.distributor.phone})")
        notify("Online demo link shared" if s.mode == "Online" else "Demo details shared", [r_school(r), r_dist(r)],
               f"{r.school.name} · {human_dt(s.at)} · {s.link or s.venue}", r.no)
        audit("Demo schedule", r.no, "Details shared", fmt_dt(s.shared_at), fmt_dt(now()), "shared_at")
        s.shared_at = now()
        out["message"] = msg
    elif act == "cancel":
        t = reason(b)
        r.cancel_reason, r.cancel_by, r.cancel_at = t, g.user.name, now()
        audit("Demo request", r.no, "Cancellation requested", None, t, "cancel")
    db.session.commit()
    res = detail_json(r)
    res.update(out)
    return res


# ---------- schedule / feedback / marketing ----------
@bp.put("/requests/<int:rid>/schedule")
@login_required
def schedule(rid):
    r = get_request(rid)
    need(r, "schedule")
    b = request.get_json(silent=True) or {}
    v = {"at": req(b, "at", "Demo date & time", "datetime"), "mode": req(b, "mode", "Demo mode", choices=["Online", "Offline"]),
         "presenter": req(b, "presenter", "Myjo presenter"), "marketing": req(b, "marketing", "Marketing person"),
         "platform": req(b, "platform", "Platform", required=False, choices=["Zoom", "Google Meet", "Microsoft Teams"]),
         "link": req(b, "link", "Meeting link", "url", required=False), "venue": req(b, "venue", "Venue details", required=False),
         "agenda": req(b, "agenda", "Demo agenda", required=False), "instructions": req(b, "instructions", "Special instructions", required=False)}
    if v["at"] < now():
        raise ApiError("Demo date & time must be in the future.", field="at")
    if v["mode"] == "Online" and (not v["platform"] or not v["link"]):
        raise ApiError("Choose a platform and enter the meeting link for an online demo.", field="link")
    if v["mode"] == "Offline" and not v["venue"]:
        raise ApiError("Enter venue details for an offline demo.", field="venue")
    for who, role in ((v["presenter"], "demo"), (v["marketing"], "mkt")):
        if not User.query.filter_by(name=who, role=role, active=True).first():
            raise ApiError(f"{who} is not an active {C.ROLE_LABELS[role]} member.")
    old = r.schedule
    before = {k: getattr(old, k) for k in v} if old else None
    if old:
        for k, val in v.items():
            setattr(old, k, val)
        old.shared_at, old.reminded = None, False
    else:
        r.schedule = DemoSchedule(request_id=r.id, **v)
    audit_diff("Demo schedule", r.no, "Rescheduled" if old else "Scheduled", before, v)
    if r.status != "Demo Scheduled":
        set_status(r, "Demo Scheduled", "Demo scheduled")
    notify("Demo schedule confirmation", [r_school(r), r_dist(r), r_user(v["presenter"]), r_user(v["marketing"])],
           f"{r.school.name} · {human_dt(v['at'])} · {v['mode']}" + (f" ({v['platform']})" if v["platform"] else ""), r.no)
    db.session.commit()
    return detail_json(r)


def attach(entity, eid, ids):
    from ..models import File
    for fid in ids or []:
        if db.session.get(File, int(fid)):
            db.session.add(Attachment(entity=entity, entity_id=eid, file_id=int(fid)))


@bp.put("/requests/<int:rid>/feedback")
@login_required
def feedback(rid):
    r = get_request(rid)
    need(r, "feedback")
    b = request.get_json(silent=True) or {}
    v = {"by": req(b, "by", "Demo conducted by"), "date": req(b, "date", "Date of demo", "date"),
         "attendees": req(b, "attendees", "Persons attended from the school"),
         "designations": req(b, "designations", "Designations", required=False),
         "classes": req(b, "classes", "Classes discussed", "list", required=False, choices=C.CLASSES),
         "subjects": req(b, "subjects", "Subjects discussed", "list", required=False),
         "series": req(b, "series", "Myjo book series demonstrated", "list"),
         "interest": req(b, "interest", "Interest level", choices=C.INTEREST),
         "requirements": req(b, "requirements", "School requirements", required=False),
         "requested": req(b, "requested", "Requested", "list", required=False, choices=C.REQUESTED_ITEMS),
         "objections": req(b, "objections", "Questions or concerns", required=False),
         "competitor": req(b, "competitor", "Competitor publisher", required=False),
         "next_follow": req(b, "next_follow", "Next follow-up date", "date", required=False),
         "remarks": req(b, "remarks", "Internal remarks", required=False)}
    if v["date"] > today():
        raise ApiError("Date of demo cannot be in the future.", field="date")
    before = {k: getattr(r.feedback, k) for k in v} if r.feedback else None
    if r.feedback:
        for k, val in v.items():
            setattr(r.feedback, k, val)
    else:
        r.feedback = DemoFeedback(request_id=r.id, **v)
    attach("feedback", r.id, b.get("file_ids"))
    audit_diff("Demo feedback", r.no, "Feedback edited" if before else "Feedback submitted", before, v)
    if r.status == "Demo Scheduled":
        set_status(r, "Demo Completed", "Demo completed")
    db.session.commit()
    return detail_json(r)


@bp.put("/requests/<int:rid>/marketing")
@login_required
def marketing(rid):
    r = get_request(rid)
    need(r, "marketing")
    b = request.get_json(silent=True) or {}
    v = {"potential": req(b, "potential", "School potential", choices=C.INTEREST),
         "person": req(b, "person", "Assigned marketing person"), "dm_name": req(b, "dm_name", "Decision-maker name"),
         "dm_desig": req(b, "dm_desig", "Decision-maker designation", required=False),
         "dm_mobile": req(b, "dm_mobile", "Decision-maker mobile", "mobile", required=False),
         "dm_email": req(b, "dm_email", "Decision-maker email", "email", required=False),
         "competitor": req(b, "competitor", "Existing publisher", required=False),
         "stage": req(b, "stage", "Discussion stage", required=False, choices=C.DISCUSSION_STAGES),
         "exp_qty": req(b, "exp_qty", "Expected order quantity", "int", required=False),
         "decision_date": req(b, "decision_date", "Expected decision date", "date", required=False),
         "next_follow": req(b, "next_follow", "Next follow-up date", "date", required=False),
         "next_action": req(b, "next_action", "Next action", required=False),
         "remarks": req(b, "remarks", "Marketing remarks", required=False)}
    before = {k: getattr(r.marketing, k) for k in v} if r.marketing else None
    if r.marketing:
        for k, val in v.items():
            setattr(r.marketing, k, val)
        r.marketing.reminded_on = None
    else:
        r.marketing = MarketingFeedback(request_id=r.id, **v)
    audit_diff("Marketing feedback", r.no, "Marketing updated" if before else "Marketing feedback added", before, v)
    if r.status == "Demo Completed":
        set_status(r, "Follow-up Pending", "Moved to follow-up")
    db.session.commit()
    return detail_json(r)


@bp.post("/requests/<int:rid>/followups")
@login_required
def add_followup(rid):
    r = get_request(rid)
    need(r, "followup")
    b = request.get_json(silent=True) or {}
    v = {"at": req(b, "at", "Follow-up date & time", "datetime"), "method": req(b, "method", "Method", choices=C.FOLLOWUP_METHODS),
         "person": req(b, "person", "Person contacted"), "summary": req(b, "summary", "Discussion summary"),
         "next_action": req(b, "next_action", "Next action", required=False),
         "next_date": req(b, "next_date", "Next follow-up date", "date", required=False)}
    if v["next_date"] and v["next_date"] < v["at"].date():
        raise ApiError("Next follow-up date must be after this follow-up.", field="next_date")
    db.session.add(FollowUp(request_id=r.id, by=g.user.name, **v))
    audit("Follow-up", r.no, "Follow-up logged", None, f"{v['method']} · {v['summary']}", "followup")
    if not r.marketing:
        r.marketing = MarketingFeedback(request_id=r.id, potential="Medium", dm_name=r.school.contact, person=g.user.name)
    if v["next_date"]:
        audit("Marketing feedback", r.no, "Next follow-up updated", r.marketing.next_follow, v["next_date"], "next_follow")
        r.marketing.next_follow, r.marketing.reminded_on = v["next_date"], None
        r.marketing.next_action = v["next_action"] or r.marketing.next_action
    if r.status == "Demo Completed":
        set_status(r, "Follow-up Pending", "Moved to follow-up")
    db.session.commit()
    return detail_json(r), 201


# ---------- Myjo order status ----------
@bp.put("/requests/<int:rid>/order")
@login_required
def order_status(rid):
    r = get_request(rid)
    need(r, "order")
    return apply_order_status(r, request.get_json(silent=True) or {})


def apply_order_status(r, b):
    """Myjo (Marketing/Admin) order decision; confirming converts the school and sets up academic support."""
    st = req(b, "order_status", "Order status", choices=C.ORDER_STATUSES)
    conf = st in C.CONFIRMED
    if r.status == "Converted" and not conf and g.user.role != "admin":
        raise ApiError("This school is already converted. Only Admin can move a confirmed order back.", 403)
    pack_in = None
    if conf:
        o = read_order(b, r)
        if r.status != "Converted" and not r.pack:
            pack_in = read_pack(b.get("pack"))
    audit("Order", r.no, "Order status changed", r.order_status, st, "order_status")
    old_status, r.order_status = r.order_status, st
    msg = "Order status saved"
    if conf:
        before = {k: getattr(r.order, k) for k in o} if r.order else None
        set_order(r, o, "myjo")
        audit_diff("Order", r.no, "Order updated" if before else "Order confirmed", before, o)
        d = r.dist_order
        if d and d.status == "Submitted":
            audit("Distributor order", r.no, "Accepted", "Submitted", f"Accepted · {o['po']}", "status")
            d.status, d.reviewed_by, d.reviewed_at = "Accepted", g.user.name, now()
            notify("Distributor order accepted", [r_dist(r)], f"{r.school.name} · {o['po']} · {o['qty']:,} books confirmed", r.no)
        if r.status != "Converted":
            convert(r, "Converted")
            db.session.flush()
            pk = create_pack(r, pack_in) if pack_in else None
            notify("Order confirmation", [r_school(r), r_dist(r), r_user(r.marketing.person) if r.marketing else None,
                                          r_team("acad", "Academic Support Team")],
                   f"{r.school.name} · {o['po']} · {o['qty']:,} books · academic support set up", r.no)
            msg = "Order confirmed · " + pack_summary(pk)
        else:
            ensure_school_user(r)
    elif st in C.LOST:
        set_status(r, "Not Converted", "Marked not converted")
        if r.dist_order and r.dist_order.status in ("Submitted", "Returned", "Accepted"):
            audit("Distributor order", r.no, "Closed", r.dist_order.status, "Rejected (school lost)", "status")
            r.dist_order.status = "Rejected"
        deactivate_school_user(r, "school marked " + st)
        msg = "Marked as not converted"
    else:
        if r.status in ("Converted", "Not Converted"):
            set_status(r, "Follow-up Pending", "Reopened for follow-up")
        if st == "Quotation Sent" and old_status != st:
            notify("Quotation shared", [r_school(r), r_dist(r)], f"{r.school.name} · quotation shared by {g.user.name}", r.no)
    db.session.commit()
    res = detail_json(r)
    res["message"] = msg
    return res


# ---------- distributor orders ----------
def require_dist(r):
    if g.user.role != "dist" or r.distributor_id != g.user.id:
        raise ApiError("Only the school's distributor can do this.", 403)


def dist_order_fields(o, b, status, direct):
    return {"status": status, "direct": direct, "ay": o["ay"], "po": o["po"], "series": o["series"], "classes": o["classes"],
            "subjects": o["subjects"], "qty": o["qty"], "req_delivery": o["del_date"], "remarks": o["remarks"],
            "by": g.user.name, "at": now(), "review_note": None, "reviewed_by": None, "reviewed_at": None}


def finalize_dist_order(r, b, o, pack_in):
    """Distributor's final order: converts the school and sets up academic support."""
    fields = dist_order_fields(o, b, "Accepted", True)
    fields.update(review_note="Final order created by the distributor; no Myjo approval needed",
                  reviewed_by=g.user.name, reviewed_at=now())
    if r.dist_order:
        for k, v in fields.items():
            setattr(r.dist_order, k, v)
    else:
        r.dist_order = DistOrder(request_id=r.id, **fields)
    attach("dist_order", r.id, b.get("file_ids"))
    audit("Order", r.no, "Order status changed", r.order_status, b.get("order_status") or "Order Confirmed", "order_status")
    r.order_status = b.get("order_status") if b.get("order_status") in C.CONFIRMED else "Order Confirmed"
    set_order(r, o, "distributor")
    audit_diff("Order", r.no, "Order created and confirmed by distributor", None, o)
    convert(r, "Converted (distributor order)")
    db.session.flush()
    pk = create_pack(r, pack_in)
    notify("Order confirmation", [r_school(r), r_dist(r), r_team("mkt", "Myjo Marketing Team"), r_team("acad", "Academic Support Team")],
           f"{r.school.name} · {o['po']} · {o['qty']:,} books · order confirmed by {r.distributor.org} · academic support set up", r.no)
    return "Order confirmed · " + pack_summary(pk)


@bp.post("/requests/<int:rid>/dist-order")
@login_required
def place_dist_order(rid):
    r = get_request(rid)
    require_dist(r)
    b = request.get_json(silent=True) or {}
    final = can("directConfirm")
    if not (("dist_order" in actions_for(r)) or (final and "dist_confirm" in actions_for(r))):
        raise ApiError("An order cannot be placed for this school right now.", 409)
    o = read_order(b, r)
    if final:
        pack_in = read_pack(b.get("pack"))
        msg = finalize_dist_order(r, b, o, pack_in)
    else:
        msg = submit_dist_order(r, b, o)
    db.session.commit()
    res = detail_json(r)
    res["message"] = msg
    return res, 201


def submit_dist_order(r, b, o):
    """Distributor without 'confirm orders directly': the order waits for Myjo Marketing to accept, return or reject."""
    before = r.dist_order and {"po": r.dist_order.po, "qty": r.dist_order.qty, "status": r.dist_order.status}
    fields = dist_order_fields(o, b, "Submitted", False)
    if r.dist_order:
        for k, v in fields.items():
            setattr(r.dist_order, k, v)
    else:
        r.dist_order = DistOrder(request_id=r.id, **fields)
    attach("dist_order", r.id, b.get("file_ids"))
    audit_diff("Distributor order", r.no, "Order resubmitted" if before else "Order placed", before,
               {"po": o["po"], "qty": o["qty"], "status": "Submitted"})
    if r.status == "Demo Completed":
        set_status(r, "Follow-up Pending", "Moved to follow-up")
    ensure_school_user(r)
    notify("Distributor order received", [r_user(r.marketing.person) if r.marketing else None, r_team("mkt", "Myjo Marketing Team"),
                                          r_team("acad", "Academic Support Team")],
           f"{r.school.name} · {o['po']} · {o['qty']:,} books · placed by {r.distributor.org}", r.no)
    return "Order placed · Myjo Marketing will confirm"


@bp.put("/requests/<int:rid>/dist-order")
@login_required
def update_dist_order(rid):
    r = get_request(rid)
    require_dist(r)
    need(r, "dist_update")
    b = request.get_json(silent=True) or {}
    o = read_order(b, r)
    before = {k: getattr(r.order, k) for k in o}
    set_order(r, o, "distributor")
    if b.get("order_status") in C.CONFIRMED:
        r.order_status = b["order_status"]
    d = r.dist_order
    d.ay, d.po, d.series, d.classes, d.subjects, d.qty, d.req_delivery, d.remarks = (
        o["ay"], o["po"], o["series"], o["classes"], o["subjects"], o["qty"], o["del_date"], o["remarks"])
    attach("dist_order", r.id, b.get("file_ids"))
    audit_diff("Order", r.no, "Order updated by distributor", before, o)
    notify("Distributor order updated", [r_team("mkt", "Myjo Marketing Team"), r_team("acad", "Academic Support Team")],
           f"{r.school.name} · {o['po']} · {o['qty']:,} books · payment {o['payment']} · delivery {human_d(o['del_date'])}", r.no)
    db.session.commit()
    res = detail_json(r)
    res["message"] = "Order updated"
    return res


@bp.post("/requests/<int:rid>/dist-order/<string:act>")
@login_required
def review_dist_order(rid, act):
    r = get_request(rid)
    if act not in ("accept", "return", "reject"):
        raise ApiError("Unknown action.", 404)
    need(r, f"{act}_dist")
    b = request.get_json(silent=True) or {}
    d = r.dist_order
    if act == "accept":
        return apply_order_status(r, {**b, "order_status": b.get("order_status") or "Order Confirmed"})
    t = req(b, "reason", "Reason")
    new = "Returned" if act == "return" else "Rejected"
    audit("Distributor order", r.no, "Returned for changes" if act == "return" else "Rejected", d.status, f"{new} · {t}", "status")
    d.status, d.review_note, d.reviewed_by, d.reviewed_at = new, t, g.user.name, now()
    if new == "Rejected" and r.status != "Converted":
        deactivate_school_user(r, "distributor order rejected")
    notify(f"Distributor order {new.lower()}", [r_dist(r)], f"{r.school.name} · {d.po} · {t}", r.no)
    db.session.commit()
    return detail_json(r)


# ---------- new school + final order in one step ----------
@bp.post("/direct-orders")
@login_required
def direct_order():
    require_perm("placeOrder")
    final = can("directConfirm")
    b = request.get_json(silent=True) or {}
    school, dist = read_school(b), pick_distributor(b)
    ay = req(b, "ay", "Academic year", choices=C.ACADEMIC_YEARS)
    ob = {**(b.get("order") or {}), "ay": ay}
    check_duplicate(school["name"], school["city"], ay)
    o = read_order(ob)
    pack_in = read_pack(b.get("pack")) if final else None
    fields = {"ay": ay, "classes": o["classes"], "subjects": o["subjects"], "series": o["series"], "exp_qty": o["qty"],
              "pref_date": None, "pref_time": None}
    r = new_request(school, fields, dist, status="Follow-up Pending", direct=True,
                    remarks="Direct order from distributor (no demo)")
    from ..models import ReviewNote
    db.session.add(ReviewNote(request_id=r.id, at=now(), by=g.user.name, type="Direct order",
                              text="School added by the distributor with a " + ("final book order." if final else "book order for Myjo review.")))
    audit("Demo request", r.no, "Created with distributor order", None, "Follow-up Pending", "status")
    msg = finalize_dist_order(r, ob, o, pack_in) if final else submit_dist_order(r, ob, o)
    db.session.commit()
    res = detail_json(r)
    res["message"] = msg
    return res, 201
