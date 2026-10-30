"""School portal: a school sees only its own published material."""
from flask import Blueprint, g, request
from .. import constants as C
from ..extensions import db
from ..models import DemoRequest, Download, Notification, PaperRevocation, QuestionPaper, Resource, Training, TrainingHistory
from ..security import login_required
from ..services.academic import academic_eligible, trainings_for, visible_resources_for
from ..services.audit import audit
from ..services.notify import notify, r_team, r_user
from ..util import ApiError, fmt_d, fmt_dt, human_d, next_no, now, req, today
from .files import file_json, record_link_view

bp = Blueprint("portal", __name__)


def my_school():
    if g.user.role != "school":
        raise ApiError("Only for school users.", 403)
    r = db.session.get(DemoRequest, g.user.school_request_id)
    if not r or not academic_eligible(r):
        raise ApiError("The Academic Support & Resource Library opens once your school has a Myjo book order.", 403)
    return r


def order_of(r):
    o = r.order or r.dist_order
    return {"status": "Confirmed" if r.status == "Converted" else "Awaiting", "ay": o.ay, "po": o.po, "series": o.series,
            "classes": o.classes, "subjects": o.subjects, "qty": o.qty,
            "delivery": fmt_d(r.order.del_date if r.order else r.dist_order.req_delivery)}


def my_papers(r):
    rows = QuestionPaper.query.filter(QuestionPaper.request_id == r.id, QuestionPaper.status.in_(C.PAPER_LIVE),
                                      QuestionPaper.cancelled.is_(False), QuestionPaper.qp_file_id.isnot(None)).all()
    return [p for p in rows if not db.session.get(PaperRevocation, (p.id, r.id))]


def my_sessions(r):
    return [t for t in trainings_for(r.id) if t.status != "Draft"]


def res_json(x):
    return {"id": x.id, "no": x.no, "title": x.title, "type": x.type, "series": x.series, "cls": x.cls, "subject": x.subject,
            "ay": x.ay, "description": x.description, "version": x.version, "file": file_json(x.file), "link": x.link}


@bp.get("/portal/overview")
@login_required
def overview():
    r = my_school()
    up = [t for t in my_sessions(r) if t.status == "Scheduled" and not t.cancelled]
    up.sort(key=lambda t: t.at)
    updates = Notification.query.filter(Notification.message.contains(r.school.name)).order_by(Notification.at.desc(), Notification.id.desc()).limit(6).all()
    return {"school": {"name": r.school.name, "city": r.school.city, "state": r.school.state, "board": r.school.board},
            "order": order_of(r),
            "upcoming_trainings": [{"id": t.id, "title": t.title, "at": fmt_dt(t.at), "mode": t.mode, "trainer": t.trainer,
                                    "expected": next(s.expected for s in t.schools if s.request_id == r.id),
                                    "confirm": next(s.school_confirm for s in t.schools if s.request_id == r.id)} for t in up],
            "updates": [{"at": fmt_dt(n.at), "event": n.event, "message": n.message} for n in updates],
            "kpis": {"papers": len(my_papers(r)), "resources": len(visible_resources_for(r)), "upcoming": len(up),
                     "my_downloads": Download.query.filter_by(request_id=r.id, user_id=g.user.id).count()}}


@bp.get("/portal/trainings")
@login_required
def trainings():
    r = my_school()
    mine = {x.id for x in visible_resources_for(r)}
    out = []
    for t in my_sessions(r):
        s = next(x for x in t.schools if x.request_id == r.id)
        out.append({"id": t.id, "no": t.no, "title": t.title, "type": t.type, "status": "Cancelled" if t.cancelled else t.status,
                    "at": fmt_dt(t.at), "mode": t.mode, "link": t.link if t.status == "Scheduled" else None, "venue": t.venue,
                    "trainer": t.trainer, "trainer_contact": _contact(t.trainer), "series": t.series, "classes": t.classes,
                    "subjects": t.subjects, "agenda": t.agenda, "instructions": t.instructions,
                    "mine": {"expected": s.expected, "confirm": s.school_confirm, "teachers": s.school_teachers,
                             "attended": s.attended, "attendance": s.attendance,
                             "feedback": {"rating": s.fb_rating, "text": s.fb_text} if s.fb_rating else None},
                    "resources": [res_json(x) for x in Resource.query.filter(Resource.id.in_(t.resource_ids or [0])) if x.id in mine],
                    "can_confirm": t.status == "Scheduled" and not t.cancelled,
                    "can_feedback": t.status in ("Completed", "Closed") and not t.cancelled})
    return {"items": out}


def _contact(name):
    from ..models import User
    u = User.query.filter_by(name=name).first()
    return f"{u.email} · {u.phone}" if u else None


def _my_row(t, r):
    s = next((x for x in t.schools if x.request_id == r.id), None)
    if not s or t.status == "Draft":
        raise ApiError("Session not found.", 404)
    return s


@bp.post("/portal/trainings/<int:tid>/confirm")
@login_required
def confirm(tid):
    r = my_school()
    t = db.session.get(Training, tid) or _nf()
    s = _my_row(t, r)
    if t.status != "Scheduled" or t.cancelled:
        raise ApiError("This session is no longer open for confirmation.", 409)
    b = request.get_json(silent=True) or {}
    c = req(b, "confirm", "Will your school attend?", choices=["Confirmed", "Declined"])
    n = 0 if c == "Declined" else req(b, "teachers", "Number of teachers attending", "int")
    if c == "Confirmed" and n <= 0:
        raise ApiError("Enter how many teachers will attend.", field="teachers")
    audit("Teacher training", t.no, "School confirmation", f"{s.school_confirm or ''} {s.school_teachers or ''}", f"{c} {n} · {r.school.name}", "school_confirm")
    s.school_confirm, s.school_teachers = c, n
    note = (b.get("note") or "").strip()
    db.session.add(TrainingHistory(training_id=t.id, at=now(), by=g.user.name, school=r.school.name,
                                   action=f"School {c.lower()}" + (f" · {n} teachers" if n else "") + (f" · {note}" if note else "")))
    notify("Training attendance confirmation", [r_user(t.trainer), r_team("acad", "Academic Support Team")],
           f"{t.no} · {r.school.name} · {c}" + (f" · {n} teachers" if n else ""), t.no)
    db.session.commit()
    return {"ok": True}


@bp.post("/portal/trainings/<int:tid>/feedback")
@login_required
def feedback(tid):
    r = my_school()
    t = db.session.get(Training, tid) or _nf()
    s = _my_row(t, r)
    if t.status not in ("Completed", "Closed"):
        raise ApiError("Feedback opens after the session is completed.", 409)
    b = request.get_json(silent=True) or {}
    rating = req(b, "rating", "Overall rating", "int")
    if not 1 <= rating <= 5:
        raise ApiError("Rating must be between 1 and 5.", field="rating")
    att = req(b, "attended", "Number of teachers who attended", "int")
    text = req(b, "text", "Feedback from your school")
    audit("Teacher training", t.no, "School feedback edited" if s.fb_rating else "School feedback submitted",
          f"{s.fb_rating or ''}", f"{rating}★ {text} · {r.school.name}", "school_feedback")
    s.fb_rating, s.fb_text, s.fb_attended, s.fb_by, s.fb_at, s.school_teachers = rating, text, att, g.user.name, now(), att
    db.session.add(TrainingHistory(training_id=t.id, at=now(), by=g.user.name, school=r.school.name,
                                   action=f"School feedback {rating}★ · {att} teachers attended"))
    notify("School training feedback received", [r_user(t.trainer), r_team("acad", "Academic Support Team")],
           f"{t.no} · {r.school.name} · {rating}★", t.no)
    db.session.commit()
    return {"ok": True}


def _nf():
    raise ApiError("Session not found.", 404)


@bp.get("/portal/library")
@login_required
def library():
    r = my_school()
    a = request.args
    q = (a.get("q") or "").lower()
    papers = [p for p in my_papers(r)
              if (not a.get("cls") or p.cls == a["cls"]) and (not a.get("subject") or p.subject == a["subject"])
              and (not a.get("series") or p.series == a["series"]) and (not a.get("ay") or p.ay == a["ay"])
              and (not a.get("exam") or p.exam == a["exam"]) and not a.get("type")
              and (not q or q in f"{p.no} {p.subject} {p.series} {p.exam}".lower())]
    res = [x for x in visible_resources_for(r)
           if (not a.get("cls") or x.cls in (a["cls"], "All classes")) and (not a.get("subject") or x.subject == a["subject"])
           and (not a.get("series") or x.series == a["series"]) and (not a.get("ay") or x.ay == a["ay"])
           and (not a.get("type") or x.type == a["type"]) and not a.get("exam")
           and (not q or q in f"{x.title} {x.type} {x.series} {x.description or ''}".lower())]
    return {"papers": [{"id": p.id, "no": p.no, "cls": p.cls, "subject": p.subject, "series": p.series, "exam": p.exam,
                        "ay": p.ay, "max_marks": p.max_marks, "published_at": fmt_dt(p.published_at),
                        "qp_file": file_json(p.qp_file), "ak_file": file_json(p.ak_file)} for p in papers],
            "resources": [res_json(x) for x in res],
            "series": (r.order or r.dist_order).series}


@bp.post("/portal/resources/<int:xid>/open")
@login_required
def open_link(xid):
    r = my_school()
    x = next((x for x in visible_resources_for(r) if x.id == xid), None)
    if not x or not x.link:
        raise ApiError("This resource is no longer available to your school.", 403)
    record_link_view(r, x)
    db.session.commit()
    return {"link": x.link}


@bp.post("/portal/papers")
@login_required
def request_paper():
    r = my_school()
    b = request.get_json(silent=True) or {}
    v = {"ay": req(b, "ay", "Academic year", choices=C.ACADEMIC_YEARS), "series": req(b, "series", "Book series"),
         "cls": req(b, "cls", "Class", choices=C.CLASSES), "subject": req(b, "subject", "Subject"),
         "exam": req(b, "exam", "Exam type", choices=C.EXAM_TYPES), "due_date": req(b, "due_date", "Required delivery date", "date"),
         "max_marks": req(b, "max_marks", "Maximum marks", "int"), "remarks": req(b, "remarks", "Remarks", required=False)}
    if v["due_date"] < today():
        raise ApiError("Required date cannot be in the past.", field="due_date")
    p = QuestionPaper(no=next_no("paper", "QP-"), request_id=r.id, status="New", raised_by="School", **v)
    db.session.add(p)
    db.session.flush()
    audit("Question paper", p.no, "Requested by school", None, f"{p.exam} · Class {p.cls} {p.subject}", "status")
    notify("Question-paper request received", [r_team("acad", "Academic Support Team")], f"{p.no} · {r.school.name} · due {human_d(p.due_date)}", p.no)
    db.session.commit()
    return {"id": p.id, "no": p.no}, 201


@bp.get("/portal/requests")
@login_required
def my_requests():
    r = my_school()
    rows = QuestionPaper.query.filter_by(request_id=r.id, cancelled=False).order_by(QuestionPaper.id.desc()).all()
    out = []
    for p in rows:
        live = p.status in C.PAPER_LIVE and not db.session.get(PaperRevocation, (p.id, r.id))
        out.append({"id": p.id, "no": p.no, "cls": p.cls, "subject": p.subject, "exam": p.exam, "due_date": fmt_d(p.due_date),
                    "status": "Published" if live else "Closed" if p.status == "Closed" else ("New" if p.status == "New" else "In Progress")})
    return {"items": out}


@bp.get("/portal/history")
@login_required
def my_history():
    r = my_school()
    rows = Download.query.filter_by(request_id=r.id).order_by(Download.at.desc(), Download.id.desc()).all()
    return {"items": [{"at": fmt_dt(d.at), "user": d.user_name, "kind": d.kind, "item": d.item, "file": d.file_name} for d in rows]}
