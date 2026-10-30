"""Order rules, academic eligibility/coverage, school logins and the academic support pack."""
import re
from flask import g
from sqlalchemy import func
from ..constants import PAPER_LIVE, ACCESS_ALL
from ..extensions import db
from ..models import (AcademicPack, DemoRequest, DistOrder, Order, QuestionPaper, Resource, ResourceRevocation,
                      ResourceSchool, Series, Subject, Training, TrainingHistory, TrainingSchool, User)
from ..security import hash_secret
from ..util import ApiError, human_d, human_dt, next_no, now, plural, req, today
from .audit import audit
from .notify import notify, r_school, r_team, r_user

TEMP_PASSWORD = "Myjo@123"   # only used when the caller does not choose one; user must change it at first sign-in
TEMP_PIN = "2580"


def active_series():
    return [s.name for s in Series.query.filter_by(active=True).order_by(Series.id)]


def active_subjects():
    return [s.name for s in Subject.query.filter_by(active=True).order_by(Subject.id)]


# ---------- eligibility & coverage ----------
def academic_eligible(r: DemoRequest):
    """A school gets academic support when its order is confirmed, or while a distributor order awaits review."""
    if r.cancelled:
        return False
    if r.status == "Converted":
        return True
    return bool(r.dist_order and r.dist_order.status in ("Submitted", "Returned") and r.status != "Not Converted")


def eligible_requests():
    rows = DemoRequest.query.filter(DemoRequest.cancelled.is_(False)).all()
    return [r for r in rows if academic_eligible(r)]


def trainings_for(request_id):
    return (Training.query.join(TrainingSchool).filter(TrainingSchool.request_id == request_id)
            .order_by(Training.at.desc()).all())


def visible_resources_for(r):
    q = Resource.query.filter(Resource.status == "Published", Resource.cancelled.is_(False))
    out = []
    revoked = {x.resource_id for x in ResourceRevocation.query.filter_by(request_id=r.id)}
    selected = {x.resource_id for x in ResourceSchool.query.filter_by(request_id=r.id)}
    for res in q:
        if res.id in revoked:
            continue
        if res.access == ACCESS_ALL or res.id in selected:
            out.append(res)
    return out


def coverage(r):
    """Training counts only when it is real (Scheduled/Completed/Closed); drafts do not count."""
    tr = any(t.status in ("Scheduled", "Completed", "Closed") and not t.cancelled for t in trainings_for(r.id))
    qp = QuestionPaper.query.filter_by(request_id=r.id, cancelled=False).count() > 0
    res = len(visible_resources_for(r)) > 0
    missing = [m for m, ok in (("teacher training", tr), ("question papers", qp), ("manuals", res)) if not ok]
    return {"training": tr, "papers": qp, "resources": res, "complete": not missing, "missing": missing}


# ---------- orders ----------
def po_in_use(po, exclude_request_id=None):
    p = po.strip().lower()
    o = Order.query.filter(func.lower(Order.po) == p, Order.request_id != (exclude_request_id or 0)).first()
    if o:
        return db.session.get(DemoRequest, o.request_id)
    d = DistOrder.query.filter(func.lower(DistOrder.po) == p, DistOrder.request_id != (exclude_request_id or 0),
                               DistOrder.status != "Rejected").first()
    return db.session.get(DemoRequest, d.request_id) if d else None


def read_order(body, r=None, need_status=True):
    """Validate the order fields shared by every order path."""
    from ..constants import ACADEMIC_YEARS, CLASSES, PAYMENT_STATUSES
    o = {
        "ay": req(body, "ay", "Academic year", choices=ACADEMIC_YEARS),
        "po": req(body, "po", "PO / reference no."),
        "series": req(body, "series", "Book series", "list", choices=active_series() + ([*(r.order.series if r and r.order else [])])),
        "classes": req(body, "classes", "Classes", "list", choices=CLASSES),
        "subjects": req(body, "subjects", "Subjects", "list", choices=active_subjects() + ([*(r.order.subjects if r and r.order else [])])),
        "qty": req(body, "qty", "Quantity ordered", "int"),
        "conf_date": req(body, "conf_date", "Order confirmation date", "date"),
        "del_date": req(body, "del_date", "Expected delivery date", "date"),
        "payment": req(body, "payment", "Payment status", choices=PAYMENT_STATUSES),
        "remarks": req(body, "remarks", "Remarks", required=False),
    }
    if o["qty"] <= 0:
        raise ApiError("Quantity ordered must be greater than zero.", field="qty")
    if o["conf_date"] > today():
        raise ApiError("Confirmation date cannot be in the future.", field="conf_date")
    if o["del_date"] < o["conf_date"]:
        raise ApiError("Expected delivery cannot be before the confirmation date.", field="del_date")
    other = po_in_use(o["po"], r.id if r else None)
    if other:
        raise ApiError(f"PO / reference number is already used by {other.school.name}.", 409, "po")
    return o


def read_pack(body):
    from ..constants import EXAM_TYPES
    p = body or {}
    out = {
        "training_at": req(p, "training_at", "Preferred training date & time", "datetime"),
        "training_mode": req(p, "training_mode", "Training mode", choices=["Offline", "Online"]),
        "teachers": req(p, "teachers", "Teachers who will attend", "int"),
        "venue": req(p, "venue", "Training venue", required=False),
        "link": req(p, "link", "Meeting link", "url", required=False),
        "exams": req(p, "exams", "Question papers needed", "list", choices=EXAM_TYPES),
        "papers_by": req(p, "papers_by", "First question papers needed by", "date"),
    }
    if out["training_at"] < now():
        raise ApiError("Preferred training date & time must be in the future.", field="training_at")
    if out["teachers"] <= 0:
        raise ApiError("Enter how many teachers will attend the training.", field="teachers")
    if out["papers_by"] < today():
        raise ApiError("Question papers needed-by date cannot be in the past.", field="papers_by")
    return out


def set_order(r, o, source):
    if r.order:
        for k, v in o.items():
            setattr(r.order, k, v)
        r.order.source = source
    else:
        r.order = Order(request_id=r.id, source=source, **o)


def set_status(r, status, action, note=None):
    old = r.status
    r.status = status
    audit("Demo request", r.no, action, old, status, "status")
    if note:
        from ..models import ReviewNote
        db.session.add(ReviewNote(request_id=r.id, at=now(), by=g.user.name, type=action, text=note))


# ---------- school logins ----------
def unique_username(base):
    b = re.sub(r"[^a-z0-9._-]", "", (base or "user").lower()) or "user"
    n, i = b, 2
    while User.query.filter_by(username=n).first():
        n, i = f"{b}{i}", i + 1
    return n


def ensure_school_user(r):
    u = User.query.filter_by(school_request_id=r.id).first()
    if u:
        if not u.active:
            u.active = True
            u.token_version += 1
            audit("User", u.email, "Reactivated", "Inactive", "Active (order placed)", "active")
        return u
    s = r.school
    email = s.email
    if User.query.filter_by(email=email).first():
        email = f"{r.no.lower()}.{email}"
    u = User(username=unique_username(re.sub(r"[^A-Za-z0-9]+", ".", s.name.split(",")[0]).strip(".")), name=s.contact,
             email=email, phone=s.mobile, role="school", school_request_id=r.id, active=True,
             pw_hash=hash_secret(TEMP_PASSWORD), pin_hash=hash_secret(TEMP_PIN), must_change=True)
    db.session.add(u)
    db.session.flush()
    audit("User", u.email, "School login created", None, f"{u.name} · {s.name} · username {u.username}", "user")
    notify("School portal login created", [r_school(r)],
           f"Username {u.username} · Myjo will share your temporary password and PIN separately", r.no)
    return u


def deactivate_school_user(r, why):
    u = User.query.filter_by(school_request_id=r.id, active=True).first()
    if u:
        u.active = False
        u.token_version += 1
        audit("User", u.email, "Deactivated", "Active", f"Inactive · {why}", "active")


# ---------- academic support pack ----------
SUBJECT_KEY = {"Mathematics": "Maths", "English": "English", "Science": "Science", "EVS": "EVS", "Hindi": "Hindi",
               "Computer Science": "Computer", "Urdu": "Urdu"}


def series_for(subject, series):
    key = SUBJECT_KEY.get(subject)
    for s in series:
        if key and key in s:
            return s
    for s in series:
        if subject.lower().split(" ")[0] in s.lower():
            return s
    return series[0]


def least_loaded(kind):
    people = [u.name for u in User.query.filter_by(role="acad", active=True).order_by(User.id)]
    if not people:
        return None
    if kind == "tr":
        load = {p: Training.query.filter(Training.trainer == p, Training.status.in_(["Draft", "Scheduled"]),
                                         Training.cancelled.is_(False)).count() for p in people}
    else:
        load = {p: QuestionPaper.query.filter(QuestionPaper.assignee == p,
                                              QuestionPaper.status.notin_(list(PAPER_LIVE) + ["Closed"]),
                                              QuestionPaper.cancelled.is_(False)).count() for p in people}
    return sorted(people, key=lambda p: load[p])[0]


def create_pack(r, p):
    """Training session + question-paper requests + manuals shared, created with the order."""
    if r.pack:
        return None
    o, at = r.order, now()
    trainer = least_loaded("tr")
    online = p["training_mode"] == "Online"
    scheduled = (not online) or bool(p.get("link"))
    t = Training(no=next_no("training", "TR-"), title="Orientation: " + " & ".join(o.series), type="Product orientation",
                 ay=o.ay, series=o.series, classes=o.classes, subjects=o.subjects, at=p["training_at"], mode=p["training_mode"],
                 trainer=trainer or "Academic Support Team",
                 agenda=f"Orientation on {', '.join(o.series)} for Classes {', '.join(o.classes)} ({', '.join(o.subjects)})",
                 link=p.get("link") if online else None,
                 venue=None if online else (p.get("venue") or f"{r.school.address}, {r.school.city} {r.school.pincode}"),
                 remarks=f"Created automatically from order {o.po}", status="Scheduled" if scheduled else "Draft")
    t.schools.append(TrainingSchool(request_id=r.id, expected=p["teachers"], school_confirm="Confirmed", school_teachers=p["teachers"]))
    res = [x for x in Resource.query.filter(Resource.status == "Published", Resource.cancelled.is_(False),
                                            Resource.series.in_(o.series))]
    for x in res:
        if x.access != ACCESS_ALL and not db.session.get(ResourceSchool, (x.id, r.id)):
            db.session.add(ResourceSchool(resource_id=x.id, request_id=r.id))
            audit("Resource", x.no, "Shared with school", None, f"{r.school.name} · order {o.po}", "schools")
        rv = db.session.get(ResourceRevocation, (x.id, r.id))
        if rv:
            db.session.delete(rv)
    t.resource_ids = [x.id for x in res]
    db.session.add(t)
    db.session.flush()
    db.session.add(TrainingHistory(training_id=t.id, at=at, by=g.user.name, school=r.school.name,
                                   action=f"Session created from order {o.po}" + ("" if scheduled else " (draft: meeting link needed)")))
    audit("Teacher training", t.no, "Session created from order", None, f"{t.status} · {r.school.name}", "status")
    if scheduled:
        notify("Teacher-training schedule", [r_school(r), r_user(trainer)],
               f"{t.no} · {t.title} · {human_dt(t.at)} · {t.mode} · {t.link or t.venue} · Trainer {t.trainer}", t.no)
    else:
        notify("Training session needs a meeting link", [r_user(trainer), r_team("acad", "Academic Support Team")],
               f"{t.no} · {r.school.name} · {human_dt(t.at)} · add the link and schedule it", t.no)
    assignee = least_loaded("qp")
    papers = []
    for ex in p["exams"]:
        for c in o.classes:
            for sub in o.subjects:
                qp = QuestionPaper(no=next_no("paper", "QP-"), request_id=r.id, ay=o.ay, cls=c, subject=sub,
                                   series=series_for(sub, o.series), exam=ex, due_date=p["papers_by"], assignee=assignee,
                                   status="Assigned" if assignee else "New", raised_by="Order",
                                   remarks=f"Created automatically from order {o.po}")
                db.session.add(qp)
                papers.append(qp)
    db.session.flush()
    if papers:
        audit("Question paper", o.po, "Requests created from order", None, f"{len(papers)} papers · {r.school.name}", "status")
        notify("Question-paper support assignment", [r_user(assignee) or r_team("acad", "Academic Support Team")],
               f"{plural(len(papers), 'question paper')} for {r.school.name} ({', '.join(p['exams'])}) · due {human_d(p['papers_by'])}", o.po)
    if res:
        notify("Manuals shared with school", [r_school(r)],
               f"{plural(len(res), 'manual')} and resources for {', '.join(o.series)} are ready to download", o.po)
    r.pack = AcademicPack(request_id=r.id, at=at, by=g.user.name, training_id=t.id, paper_ids=[x.id for x in papers],
                          resource_ids=[x.id for x in res])
    return {"training": t, "papers": papers, "resources": res}


def pack_summary(pk):
    if not pk:
        return "school converted"
    return (f"training {'scheduled' if pk['training'].status == 'Scheduled' else 'drafted'}, "
            f"{plural(len(pk['papers']), 'question paper')} assigned, {plural(len(pk['resources']), 'manual')} shared")


def convert(r, action):
    """Mark a school Converted (after its order is saved), create its login and its academic pack."""
    set_status(r, "Converted", action)
    ensure_school_user(r)
