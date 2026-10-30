"""Marketing/orders lists, ordered schools, group teacher training, question papers, resources, downloads."""
from flask import Blueprint, g, request
from .. import constants as C
from ..extensions import db
from ..models import (DemoRequest, Download, FollowUp, PaperRevocation, QuestionPaper, Resource, ResourceRevocation,
                      ResourceSchool, Training, TrainingHistory, TrainingSchool, User, Attachment)
from ..security import can, login_required, require_perm, require_screen
from ..services.academic import (academic_eligible, active_series, active_subjects, coverage, eligible_requests,
                                 trainings_for, visible_resources_for)
from ..services.audit import audit, audit_diff
from ..services.notify import notify, r_school, r_user
from ..util import ApiError, fmt_d, fmt_dt, human_d, human_dt, next_no, now, req, today
from .files import file_json
from .requests_api import attach, dist_json, school_json

bp = Blueprint("academic", __name__)


def internal_only():
    if g.user.role in ("dist", "school"):
        raise ApiError("You do not have access to this.", 403)


# ======================= Marketing & orders =======================
@bp.get("/marketing")
@login_required
def marketing_list():
    require_screen("marketing")
    rows = [r for r in DemoRequest.query.filter(DemoRequest.cancelled.is_(False)).all()
            if (r.marketing or r.status in ("Demo Completed", "Follow-up Pending")) and r.status not in ("Converted", "Not Converted")]
    out = []
    for r in rows:
        m = r.marketing
        out.append({"id": r.id, "no": r.no, "school": school_json(r.school), "distributor": dist_json(r.distributor),
                    "status": r.status, "order_status": r.order_status,
                    "potential": m.potential if m else (r.feedback.interest if r.feedback else None),
                    "stage": m.stage if m else None, "exp_qty": (m.exp_qty if m and m.exp_qty else r.exp_qty),
                    "next_action": m.next_action if m else None, "next_follow": fmt_d(m.next_follow) if m else None,
                    "overdue": bool(m and m.next_follow and m.next_follow < today()),
                    "person": (m.person if m else (r.schedule.marketing if r.schedule else None)),
                    "dist_order_status": r.dist_order.status if r.dist_order else None})
    out.sort(key=lambda x: x["next_follow"] or "9999")
    return {"items": out, "total": len(out)}


@bp.get("/followups")
@login_required
def followups():
    require_screen("marketing", "requests")
    internal_only()
    n = min(int(request.args.get("limit", 25)), 200)
    rows = FollowUp.query.order_by(FollowUp.at.desc(), FollowUp.id.desc()).limit(n).all()
    return {"items": [{"id": f.id, "request_id": f.request_id, "school": db.session.get(DemoRequest, f.request_id).school.name,
                       "at": fmt_dt(f.at), "method": f.method, "person": f.person, "summary": f.summary,
                       "next_action": f.next_action, "next_date": fmt_d(f.next_date), "by": f.by} for f in rows]}


def order_row(r):
    o = r.order
    return {"request_id": r.id, "no": r.no, "school": r.school.name, "city": r.school.city, "ay": o.ay,
            "distributor": r.distributor.org, "series": o.series, "classes": o.classes, "subjects": o.subjects,
            "qty": o.qty, "po": o.po, "conf_date": fmt_d(o.conf_date), "del_date": fmt_d(o.del_date),
            "payment": o.payment, "order_status": r.order_status, "source": o.source}


@bp.get("/orders")
@login_required
def orders():
    require_screen("orders")
    conv = [r for r in DemoRequest.query.filter_by(status="Converted", cancelled=False) if r.order]
    pend = [r for r in DemoRequest.query.filter_by(cancelled=False) if r.dist_order and r.dist_order.status == "Submitted"]
    counts = {s: DemoRequest.query.filter_by(order_status=s, cancelled=False).count() for s in C.ORDER_STATUSES}
    return {"confirmed": [order_row(r) for r in conv],
            "pending_dist": [{"request_id": r.id, "school": r.school.name, "distributor": r.distributor.org, "po": r.dist_order.po,
                              "series": r.dist_order.series, "qty": r.dist_order.qty, "at": fmt_dt(r.dist_order.at),
                              "req_delivery": fmt_d(r.dist_order.req_delivery)} for r in pend],
            "status_counts": counts,
            "totals": {"schools": len(conv), "books": sum(r.order.qty for r in conv)}}


@bp.get("/my-orders")
@login_required
def my_orders():
    if g.user.role != "dist":
        raise ApiError("Only for distributors.", 403)
    from .requests_api import can_dist_order
    rows = DemoRequest.query.filter_by(distributor_id=g.user.id, cancelled=False).order_by(DemoRequest.created_at.desc()).all()
    can_order = [r for r in rows if can_dist_order(r) or (r.dist_order and r.dist_order.status == "Submitted")]
    placed = [r for r in rows if r.dist_order or r.order]
    return {
        "can_order": [{"id": r.id, "school": r.school.name, "city": r.school.city, "status": r.status,
                       "dist_order_status": r.dist_order.status if r.dist_order else None,
                       "review_note": r.dist_order.review_note if r.dist_order else None} for r in can_order],
        "orders": [{"id": r.id, "school": r.school.name, "po": (r.order or r.dist_order).po,
                    "series": (r.order or r.dist_order).series, "qty": (r.order or r.dist_order).qty,
                    "placed": fmt_dt(r.dist_order.at) if r.dist_order else None,
                    "status": r.order_status if r.status == "Converted" else (r.dist_order.status if r.dist_order else r.order_status),
                    "by_myjo": not r.dist_order,
                    "delivery": fmt_d(r.order.del_date if r.order else r.dist_order.req_delivery)} for r in placed],
        "kpis": {"waiting": sum(1 for r in rows if r.dist_order and r.dist_order.status == "Submitted"),
                 "returned": sum(1 for r in rows if r.dist_order and r.dist_order.status == "Returned"),
                 "confirmed": sum(1 for r in rows if r.status == "Converted"),
                 "books": sum(r.order.qty for r in rows if r.status == "Converted" and r.order)},
        "final_orders": can("directConfirm"),
    }


# ======================= Ordered schools =======================
@bp.get("/ordered-schools")
@login_required
def ordered_schools():
    require_screen("acschools")
    out = []
    for r in eligible_requests():
        o = r.order or r.dist_order
        cov = coverage(r)
        out.append({"request_id": r.id, "no": r.no, "school": r.school.name, "city": r.school.city,
                    "distributor": r.distributor.org,
                    "order": {"status": "Confirmed" if r.status == "Converted" else "Awaiting",
                              "source": "distributor" if r.dist_order else "myjo",
                              "date": fmt_d(r.order.conf_date) if r.order else fmt_d(r.dist_order.at.date()),
                              "po": o.po, "qty": o.qty, "series": o.series, "classes": o.classes, "subjects": o.subjects},
                    "counts": {"trainings": len([t for t in trainings_for(r.id) if not t.cancelled]),
                               "papers": QuestionPaper.query.filter_by(request_id=r.id, cancelled=False).count(),
                               "resources": len(visible_resources_for(r))},
                    "coverage": cov,
                    "login_active": bool(User.query.filter_by(school_request_id=r.id, active=True).first())})
    out.sort(key=lambda x: (x["coverage"]["complete"], -(int(x["order"]["date"].replace("-", "")) if x["order"]["date"] else 0)))
    return {"items": out, "total": len(out)}


def eligible_or_404(rid):
    r = db.session.get(DemoRequest, rid)
    if not r or not academic_eligible(r):
        raise ApiError("This school does not have an order yet.", field="request_id")
    return r


# ======================= Trainings =======================
def overdue_training(t):
    return t.status == "Scheduled" and not t.cancelled and t.at < now()


def training_row(t):
    return {"id": t.id, "no": t.no, "title": t.title, "type": t.type, "ay": t.ay, "at": fmt_dt(t.at), "mode": t.mode,
            "trainer": t.trainer, "status": "Cancelled" if t.cancelled else t.status,
            "schools": [{"request_id": s.request_id, "name": s.request.school.name, "expected": s.expected, "attended": s.attended} for s in t.schools],
            "expected_total": sum(s.expected for s in t.schools),
            "attended_total": sum(s.attended or 0 for s in t.schools),
            "overdue": overdue_training(t), "cancel_pending": t.cancel_pending}


def training_actions(t):
    if t.cancelled or not can("academic"):
        return []
    a = []
    if t.status in ("Draft", "Scheduled"):
        a.append("edit")
    if t.status == "Draft":
        a.append("schedule")
    if t.status == "Scheduled":
        a.append("complete")
    if t.status == "Completed":
        a += ["complete", "close"]
    if t.status in ("Draft", "Scheduled") and not t.cancel_reason:
        a.append("cancel")
    return a


def training_detail(t):
    d = training_row(t)
    res = [db.session.get(Resource, i) for i in t.resource_ids or []]
    d.update({"series": t.series, "classes": t.classes, "subjects": t.subjects, "link": t.link, "venue": t.venue, "agenda": t.agenda,
              "remarks": t.remarks, "instructions": t.instructions,
              "schools": [{"request_id": s.request_id, "name": s.request.school.name, "city": s.request.school.city,
                           "expected": s.expected, "school_confirm": s.school_confirm, "school_teachers": s.school_teachers,
                           "attended": s.attended, "attendance": s.attendance, "myjo_feedback": s.myjo_feedback,
                           "school_feedback": {"rating": s.fb_rating, "text": s.fb_text, "attended": s.fb_attended,
                                               "by": s.fb_by, "at": fmt_dt(s.fb_at)} if s.fb_rating else None} for s in t.schools],
              "resources": [{"id": x.id, "no": x.no, "title": x.title, "type": x.type, "version": x.version, "status": x.status}
                            for x in res if x],
              "completion": {**t.completion, "files": [file_json(a.file) for a in Attachment.query.filter_by(entity="training", entity_id=t.id)]} if t.completion else None,
              "history": [{"at": fmt_dt(h.at), "by": h.by, "school": h.school, "action": h.action} for h in t.history],
              "cancel": {"reason": t.cancel_reason, "by": t.cancel_by, "approved_by": t.cancel_approved_by} if t.cancel_reason else None,
              "actions": training_actions(t)})
    return d


def history(t, action, school="All schools"):
    db.session.add(TrainingHistory(training_id=t.id, at=now(), by=g.user.name, school=school, action=action))


@bp.get("/trainings")
@login_required
def list_trainings():
    require_screen("training")
    q = Training.query
    st = request.args.get("status")
    if st == "Cancelled":
        q = q.filter(Training.cancelled.is_(True))
    elif st:
        q = q.filter(Training.status == st, Training.cancelled.is_(False))
    rows = q.order_by(Training.at.desc()).all()
    return {"items": [training_row(t) for t in rows], "total": len(rows)}


@bp.get("/trainings/<int:tid>")
@login_required
def get_training(tid):
    require_screen("training")
    t = db.session.get(Training, tid)
    if not t:
        raise ApiError("Session not found.", 404)
    return training_detail(t)


def read_training(b, t=None):
    v = {"title": req(b, "title", "Training title"), "type": req(b, "type", "Training type", choices=C.TRAINING_TYPES),
         "ay": req(b, "ay", "Academic year", choices=C.ACADEMIC_YEARS),
         "series": req(b, "series", "Book series", "list", choices=active_series()),
         "classes": req(b, "classes", "Classes covered", "list", choices=C.CLASSES),
         "subjects": req(b, "subjects", "Subjects covered", "list", choices=active_subjects()),
         "at": req(b, "at", "Training date & time", "datetime"), "mode": req(b, "mode", "Training mode", choices=["Online", "Offline"]),
         "trainer": req(b, "trainer", "Trainer assigned"), "link": req(b, "link", "Online meeting link", "url", required=False),
         "venue": req(b, "venue", "Offline venue", required=False), "agenda": req(b, "agenda", "Training agenda"),
         "remarks": req(b, "remarks", "Remarks", required=False), "instructions": req(b, "instructions", "Special instructions", required=False),
         "status": req(b, "status", "Save as", choices=["Draft", "Scheduled"])}
    if not User.query.filter_by(name=v["trainer"], role="acad", active=True).first():
        raise ApiError("Choose an active Academic Support Team member as trainer.", field="trainer")
    if v["mode"] == "Online" and not v["link"]:
        raise ApiError("Enter the online meeting link.", field="link")
    if v["mode"] == "Offline" and not v["venue"]:
        raise ApiError("Enter the offline venue.", field="venue")
    if v["mode"] == "Online":
        v["venue"] = None
    else:
        v["link"] = None
    if v["status"] == "Scheduled" and v["at"] < now() and (t is None or t.at != v["at"] or t.status != "Scheduled"):
        raise ApiError("Training date & time must be in the future to schedule the session.", field="at")
    schools = b.get("schools") or []
    if not schools:
        raise ApiError("Select school(s) is required.", field="schools")
    out = []
    for s in schools:
        r = eligible_or_404(int(s.get("request_id")))
        exp = req(s, "expected", f"Expected teachers · {r.school.name}", "int")
        if exp <= 0:
            raise ApiError(f"Enter expected teachers for {r.school.name}.", field="schools")
        out.append((r, exp))
    v["resource_ids"] = [int(x) for x in b.get("resource_ids") or []]
    return v, out


def notify_schedule(t, ids, changed):
    rs = [db.session.get(DemoRequest, i) for i in ids]
    notify("Teacher-training schedule", [r_school(r) for r in rs] + [r_user(t.trainer)],
           f"{t.no} · {t.title} · {human_dt(t.at)} · {t.mode} · {t.link or t.venue} · Trainer {t.trainer}", t.no)
    history(t, "Updated schedule sent to schools" if changed else "Schedule shared with schools")


@bp.post("/trainings")
@login_required
def create_training():
    require_perm("academic")
    b = request.get_json(silent=True) or {}
    v, schools = read_training(b)
    t = Training(no=next_no("training", "TR-"), created_at=now(), **v)
    for r, exp in schools:
        t.schools.append(TrainingSchool(request_id=r.id, expected=exp))
    db.session.add(t)
    db.session.flush()
    audit("Teacher training", t.no, "Session created", None, f"{t.status} · " + "; ".join(f"{r.school.name} ({e})" for r, e in schools), "status")
    history(t, f"Session created as {t.status}")
    if t.status == "Scheduled":
        notify_schedule(t, [r.id for r, _ in schools], False)
    db.session.commit()
    return training_detail(t), 201


@bp.put("/trainings/<int:tid>")
@login_required
def edit_training(tid):
    require_perm("academic")
    t = db.session.get(Training, tid)
    if not t or "edit" not in training_actions(t):
        raise ApiError("This session can no longer be edited.", 409)
    b = request.get_json(silent=True) or {}
    v, schools = read_training(b, t)
    was = {"status": t.status, "at": t.at, "link": t.link, "venue": t.venue, "mode": t.mode, "ids": [s.request_id for s in t.schools]}
    before = {k: getattr(t, k) for k in v}
    for k, val in v.items():
        setattr(t, k, val)
    keep = {s.request_id: s for s in t.schools}
    new_ids = [r.id for r, _ in schools]
    for s in list(t.schools):
        if s.request_id not in new_ids:
            history(t, "School removed from session", s.request.school.name)
            t.schools.remove(s)
    for r, exp in schools:
        if r.id in keep:
            keep[r.id].expected = exp
        else:
            t.schools.append(TrainingSchool(request_id=r.id, expected=exp))
            history(t, "School added to session", r.school.name)
    audit_diff("Teacher training", t.no, "Session updated", before, v)
    history(t, "Session details updated")
    if t.status == "Scheduled":
        changed = was["status"] != "Scheduled" or was["at"] != t.at or was["link"] != t.link or was["venue"] != t.venue or was["mode"] != t.mode
        ids = new_ids if changed else [i for i in new_ids if i not in was["ids"]]
        if ids:
            notify_schedule(t, ids, changed and was["status"] == "Scheduled")
        if changed:
            t.reminded = False
    db.session.commit()
    return training_detail(t)


@bp.post("/trainings/<int:tid>/<string:act>")
@login_required
def training_action(tid, act):
    t = db.session.get(Training, tid)
    if not t:
        raise ApiError("Session not found.", 404)
    if act not in ("schedule", "complete", "close", "cancel"):
        raise ApiError("Unknown action.", 404)
    if act not in training_actions(t):
        raise ApiError("This action is not available for this session right now.", 409)
    b = request.get_json(silent=True) or {}
    if act == "schedule":
        if t.at < now():
            raise ApiError("Training date & time must be in the future to schedule the session.", field="at")
        if t.mode == "Online" and not t.link:
            raise ApiError("Add the meeting link before scheduling.", field="link")
        audit("Teacher training", t.no, "Scheduled", t.status, "Scheduled", "status")
        t.status = "Scheduled"
        notify_schedule(t, [s.request_id for s in t.schools], False)
    elif act == "complete":
        if t.at > now():
            raise ApiError("Completion can be recorded only after the session date & time.")
        st = req(b, "status", "Completion status", choices=["Completed", "Partially completed"])
        remarks = req(b, "trainer_remarks", "Trainer remarks")
        rows = {int(x.get("request_id")): x for x in b.get("schools") or []}
        first = not t.completion
        for s in t.schools:
            x = rows.get(s.request_id)
            if x is None:
                raise ApiError(f"Enter attendance for {s.request.school.name}.", field="schools")
            att = req(x, "attendance", f"Attendance · {s.request.school.name}", choices=["Attended", "Partially attended", "Did not attend"])
            n = req(x, "attended", f"Teachers attended · {s.request.school.name}", "int", required=att != "Did not attend") or 0
            if att == "Did not attend" and n > 0:
                raise ApiError(f'{s.request.school.name}: attendance is "Did not attend" but teachers attended is {n}.', field="schools")
            if att != "Did not attend" and n <= 0:
                raise ApiError(f"{s.request.school.name}: enter the number of teachers who attended.", field="schools")
            if s.attended != n or s.attendance != att:
                history(t, f"Attendance recorded: {n} teachers · {att}", s.request.school.name)
            s.attended, s.attendance, s.myjo_feedback = n, att, (x.get("myjo_feedback") or "").strip() or None
        t.completion = {"status": st, "trainer_remarks": remarks, "follow_up": (b.get("follow_up") or "").strip(),
                        "recording": (b.get("recording") or "").strip(), "at": fmt_dt(now()), "by": g.user.name}
        if b.get("recording"):
            req(b, "recording", "Recording link", "url")
        attach("training", t.id, b.get("file_ids"))
        if b.get("resource_ids") is not None:
            t.resource_ids = [int(i) for i in b["resource_ids"]]
        audit("Teacher training", t.no, "Completion recorded" if first else "Completion updated", t.status, "Completed", "status")
        t.status = "Completed"
        history(t, f"Completion recorded ({st})" if first else "Completion updated")
        if first:
            notify("Training completed · feedback requested",
                   [r_school(s.request) for s in t.schools if s.attendance != "Did not attend"],
                   f"{t.no} · {t.title} · please share your school's feedback in the portal", t.no)
    elif act == "close":
        note = (b.get("note") or "").strip()
        audit("Teacher training", t.no, "Closed", t.status, "Closed" + (f" · {note}" if note else ""), "status")
        t.status = "Closed"
        history(t, "Session closed" + (f": {note}" if note else ""))
    elif act == "cancel":
        t.cancel_reason, t.cancel_by, t.cancel_at = req(b, "reason", "Reason"), g.user.name, now()
        audit("Teacher training", t.no, "Cancellation requested", None, t.cancel_reason, "cancel")
    db.session.commit()
    return training_detail(t)


# ======================= Question papers =======================
def paper_row(p):
    rv = db.session.get(PaperRevocation, (p.id, p.request_id)) is not None
    return {"id": p.id, "no": p.no, "request_id": p.request_id, "school": p.request.school.name, "ay": p.ay, "cls": p.cls,
            "subject": p.subject, "series": p.series, "exam": p.exam, "due_date": fmt_d(p.due_date), "assignee": p.assignee,
            "max_marks": p.max_marks, "delivery_date": fmt_d(p.delivery_date), "remarks": p.remarks,
            "status": "Cancelled" if p.cancelled else p.status, "qp_file": file_json(p.qp_file), "ak_file": file_json(p.ak_file),
            "revoked": rv, "raised_by": p.raised_by, "published_at": fmt_dt(p.published_at),
            "overdue": paper_overdue(p), "cancel_pending": p.cancel_pending, "actions": paper_actions(p, rv)}


def paper_open(p):
    return p.status not in C.PAPER_LIVE + ("Closed",) and not p.cancelled


def paper_overdue(p):
    return paper_open(p) and p.due_date < today()


def paper_actions(p, rv=False):
    if p.cancelled:
        return []
    a = []
    if can("academic"):
        a.append("edit")
        if p.status == "Published":
            a.append("deliver")
        if not p.cancel_reason:
            a.append("cancel")
    if can("publish") and p.status in ("Assigned", "In Progress", "Ready for Review"):
        a.append("publish")
    if can("revoke") and p.status in C.PAPER_LIVE:
        a.append("restore" if rv else "revoke")
    return a


@bp.get("/papers")
@login_required
def list_papers():
    require_screen("papers")
    q = QuestionPaper.query
    st = request.args.get("status")
    if st:
        q = q.filter(QuestionPaper.status == st)
    rows = q.order_by(QuestionPaper.due_date).all()
    return {"items": [paper_row(p) for p in rows], "total": len(rows)}


def read_paper(b, p=None):
    r = eligible_or_404(int(req(b, "request_id", "School", "int")))
    v = {"request_id": r.id, "ay": req(b, "ay", "Academic year", choices=C.ACADEMIC_YEARS),
         "cls": req(b, "cls", "Class", choices=C.CLASSES), "subject": req(b, "subject", "Subject"),
         "series": req(b, "series", "Book series"), "exam": req(b, "exam", "Exam type", choices=C.EXAM_TYPES),
         "due_date": req(b, "due_date", "Required delivery date", "date"),
         "assignee": req(b, "assignee", "Assigned academic team member", required=False),
         "max_marks": req(b, "max_marks", "Maximum marks", "int", required=False),
         "delivery_date": req(b, "delivery_date", "Delivery date", "date", required=False),
         "status": req(b, "status", "Status", choices=C.PAPER_STATUSES),
         "qp_file_id": b.get("qp_file_id") or (p.qp_file_id if p else None),
         "ak_file_id": b.get("ak_file_id") or (p.ak_file_id if p else None),
         "remarks": req(b, "remarks", "Remarks", required=False)}
    if v["status"] != "New" and not v["assignee"]:
        raise ApiError("Assign an academic team member first.", field="assignee")
    if v["status"] in C.PAPER_LIVE and not v["qp_file_id"]:
        raise ApiError("Upload the question paper file before publishing.", field="qp_file_id")
    if v["status"] == "Delivered" and not v["delivery_date"]:
        raise ApiError("Enter the delivery date.", field="delivery_date")
    if v["status"] in C.PAPER_LIVE and not can("publish"):
        raise ApiError("You do not have permission to publish.", 403)
    return r, v


def after_paper_save(p, was_status, was_assignee, r):
    if p.assignee and p.assignee != was_assignee:
        notify("Question-paper support assignment", [r_user(p.assignee)],
               f"{p.no} · {r.school.name} · Class {p.cls} {p.subject} · due {human_d(p.due_date)}", p.no)
        if p.status == "New":
            audit("Question paper", p.no, "Auto status", "New", "Assigned", "status")
            p.status = "Assigned"
    if p.status in C.PAPER_LIVE and was_status not in C.PAPER_LIVE:
        p.published_at = now()
        audit("Question paper", p.no, "Published", was_status, "Published", "status")
        notify("New question paper published", [r_school(r)], f"{p.no} · Class {p.cls} {p.subject} · {p.exam} is ready to download", p.no)


@bp.post("/papers")
@login_required
def create_paper():
    require_perm("academic")
    r, v = read_paper(request.get_json(silent=True) or {})
    p = QuestionPaper(no=next_no("paper", "QP-"), raised_by="Myjo", **v)
    db.session.add(p)
    db.session.flush()
    audit("Question paper", p.no, "Created", None, p.status, "status")
    after_paper_save(p, None, None, r)
    db.session.commit()
    return paper_row(p), 201


@bp.put("/papers/<int:pid>")
@login_required
def edit_paper(pid):
    require_perm("academic")
    p = db.session.get(QuestionPaper, pid)
    if not p or p.cancelled:
        raise ApiError("Question paper not found.", 404)
    r, v = read_paper(request.get_json(silent=True) or {}, p)
    was_s, was_a = p.status, p.assignee
    before = {k: getattr(p, k) for k in v}
    for k, val in v.items():
        setattr(p, k, val)
    audit_diff("Question paper", p.no, "Updated", before, v)
    after_paper_save(p, was_s, was_a, r)
    db.session.commit()
    return paper_row(p)


@bp.post("/papers/<int:pid>/<string:act>")
@login_required
def paper_action(pid, act):
    p = db.session.get(QuestionPaper, pid)
    if not p:
        raise ApiError("Question paper not found.", 404)
    rv = db.session.get(PaperRevocation, (p.id, p.request_id))
    if act not in paper_actions(p, bool(rv)):
        raise ApiError("This action is not available for this paper right now.", 409)
    b = request.get_json(silent=True) or {}
    if act == "publish":
        if not p.qp_file_id:
            raise ApiError("Upload the question paper file before publishing.")
        was = p.status
        p.status = "Published"
        after_paper_save(p, was, p.assignee, p.request)
    elif act == "deliver":
        audit("Question paper", p.no, "Delivered", p.status, "Delivered", "status")
        p.status, p.delivery_date = "Delivered", p.delivery_date or today()
    elif act == "revoke":
        t = req(b, "reason", "Reason")
        db.session.add(PaperRevocation(paper_id=p.id, request_id=p.request_id))
        audit("Question paper", p.no, "Access revoked", "allowed", f"revoked: {t}", "access")
    elif act == "restore":
        db.session.delete(rv)
        audit("Question paper", p.no, "Access restored", "revoked", "allowed", "access")
    elif act == "cancel":
        p.cancel_reason, p.cancel_by, p.cancel_at = req(b, "reason", "Reason"), g.user.name, now()
        audit("Question paper", p.no, "Cancellation requested", None, p.cancel_reason, "cancel")
    db.session.commit()
    return paper_row(p)


# ======================= Resources =======================
def res_audience(x):
    if x.access == C.ACCESS_ALL:
        return [r.id for r in eligible_requests()]
    return [s.request_id for s in ResourceSchool.query.filter_by(resource_id=x.id)]


def res_actions(x):
    if x.cancelled:
        return []
    a = []
    if can("academic"):
        a.append("edit")
        if not x.cancel_reason:
            a.append("cancel")
    if can("publish") and x.status == "Draft":
        a.append("publish")
    if can("publish") and x.status == "Published":
        a.append("archive")
    if can("revoke") and x.status == "Published":
        a.append("access")
    return a


def res_row(x):
    schools = [s.request_id for s in ResourceSchool.query.filter_by(resource_id=x.id)]
    revoked = [s.request_id for s in ResourceRevocation.query.filter_by(resource_id=x.id)]
    name = lambda i: db.session.get(DemoRequest, i).school.name  # noqa: E731
    return {"id": x.id, "no": x.no, "title": x.title, "type": x.type, "series": x.series, "cls": x.cls, "subject": x.subject,
            "ay": x.ay, "description": x.description, "file": file_json(x.file), "link": x.link, "version": x.version,
            "upload_date": fmt_d(x.upload_date), "uploaded_by": x.uploaded_by, "access": x.access,
            "school_ids": schools, "schools": [name(i) for i in schools],
            "revoked_ids": revoked, "revoked": [name(i) for i in revoked],
            "status": "Cancelled" if x.cancelled else x.status,
            "downloads": Download.query.filter_by(item_ref=x.no).count(), "cancel_pending": x.cancel_pending,
            "audience": [{"id": i, "name": name(i)} for i in res_audience(x)], "actions": res_actions(x)}


@bp.get("/resources")
@login_required
def list_resources():
    require_screen("resources", "training")
    q = Resource.query
    if request.args.get("status"):
        q = q.filter(Resource.status == request.args["status"])
    rows = q.order_by(Resource.upload_date.desc(), Resource.id.desc()).all()
    return {"items": [res_row(x) for x in rows], "total": len(rows)}


def read_resource(b):
    v = {"title": req(b, "title", "Resource title"), "type": req(b, "type", "Resource type", choices=C.RESOURCE_TYPES),
         "series": req(b, "series", "Book series"), "cls": req(b, "cls", "Class", choices=["All classes"] + C.CLASSES),
         "subject": req(b, "subject", "Subject"), "ay": req(b, "ay", "Academic year", choices=C.ACADEMIC_YEARS),
         "version": req(b, "version", "Version number"), "description": req(b, "description", "Description", required=False),
         "file_id": b.get("file_id") or None, "link": req(b, "link", "Video link", "url", required=False),
         "access": req(b, "access", "Access level", choices=[C.ACCESS_ALL, C.ACCESS_SELECTED]),
         "status": req(b, "status", "Status", choices=["Draft", "Published", "Archived"])}
    ids = [int(i) for i in b.get("school_ids") or []]
    if not v["file_id"] and not v["link"]:
        raise ApiError("Upload a file or add a video link.", field="file_id")
    if v["access"] == C.ACCESS_SELECTED and not ids:
        raise ApiError("Choose at least one school, or set access to All Ordered Schools.", field="school_ids")
    if v["status"] != "Draft" and not can("publish"):
        raise ApiError("You do not have permission to publish.", 403)
    return v, ([] if v["access"] == C.ACCESS_ALL else ids)


def set_res_schools(x, ids):
    ResourceSchool.query.filter_by(resource_id=x.id).delete()
    for i in ids:
        eligible_or_404(i)
        db.session.add(ResourceSchool(resource_id=x.id, request_id=i))


def after_res_status(x, was):
    if x.status == "Published" and was != "Published":
        audit("Resource", x.no, "Published", was or "Draft", "Published", "status")
        manual = x.type == "Teacher training manual"
        rev = {s.request_id for s in ResourceRevocation.query.filter_by(resource_id=x.id)}
        notify("New teacher-training manual published" if manual else "New academic resource published",
               [r_school(db.session.get(DemoRequest, i)) for i in res_audience(x) if i not in rev], f"{x.title} · v{x.version}", x.no)
    if x.status == "Archived" and was != "Archived":
        audit("Resource", x.no, "Archived", was, "Archived", "status")


@bp.post("/resources")
@login_required
def create_resource():
    require_perm("academic")
    v, ids = read_resource(request.get_json(silent=True) or {})
    x = Resource(no=next_no("resource", "RES-"), upload_date=today(), uploaded_by=g.user.name, **v)
    db.session.add(x)
    db.session.flush()
    set_res_schools(x, ids)
    audit("Resource", x.no, "Uploaded", None, f"{x.title} v{x.version}", "file")
    after_res_status(x, None)
    db.session.commit()
    return res_row(x), 201


@bp.put("/resources/<int:xid>")
@login_required
def edit_resource(xid):
    require_perm("academic")
    x = db.session.get(Resource, xid)
    if not x or x.cancelled:
        raise ApiError("Resource not found.", 404)
    v, ids = read_resource(request.get_json(silent=True) or {})
    was = x.status
    before = {k: getattr(x, k) for k in v}
    if v["file_id"] != x.file_id or v["version"] != x.version:
        x.upload_date, x.uploaded_by = today(), g.user.name
    for k, val in v.items():
        setattr(x, k, val)
    set_res_schools(x, ids)
    audit_diff("Resource", x.no, "Updated", before, v)
    after_res_status(x, was)
    db.session.commit()
    return res_row(x)


@bp.post("/resources/<int:xid>/<string:act>")
@login_required
def resource_action(xid, act):
    x = db.session.get(Resource, xid)
    if not x:
        raise ApiError("Resource not found.", 404)
    if act not in res_actions(x):
        raise ApiError("This action is not available for this resource right now.", 409)
    b = request.get_json(silent=True) or {}
    was = x.status
    if act == "publish":
        x.status = "Published"
    elif act == "archive":
        x.status = "Archived"
    elif act == "cancel":
        x.cancel_reason, x.cancel_by, x.cancel_at = req(b, "reason", "Reason"), g.user.name, now()
        audit("Resource", x.no, "Cancellation requested", None, x.cancel_reason, "cancel")
    after_res_status(x, was)
    db.session.commit()
    return res_row(x)


@bp.put("/resources/<int:xid>/access")
@login_required
def resource_access(xid):
    require_perm("revoke")
    x = db.session.get(Resource, xid)
    if not x:
        raise ApiError("Resource not found.", 404)
    ids = [int(i) for i in (request.get_json(silent=True) or {}).get("revoked_ids") or []]
    before = [s.request_id for s in ResourceRevocation.query.filter_by(resource_id=x.id)]
    ResourceRevocation.query.filter_by(resource_id=x.id).delete()
    for i in ids:
        db.session.add(ResourceRevocation(resource_id=x.id, request_id=i))
    audit("Resource", x.no, "Access changed", before, ids, "revoked")
    db.session.commit()
    return res_row(x)


# ======================= Downloads =======================
@bp.get("/downloads")
@login_required
def downloads():
    require_screen("downloads")
    rid = request.args.get("request_id", type=int)
    stats = []
    for r in eligible_requests():
        ds = Download.query.filter_by(request_id=r.id).all()
        stats.append({"request_id": r.id, "school": r.school.name,
                      "papers": sum(1 for d in ds if d.kind != "Resource"), "resources": sum(1 for d in ds if d.kind == "Resource"),
                      "last": fmt_dt(max((d.at for d in ds), default=None))})
    q = Download.query
    if rid:
        q = q.filter_by(request_id=rid)
    log = q.order_by(Download.at.desc(), Download.id.desc()).limit(500).all()
    return {"by_school": sorted(stats, key=lambda s: -(s["papers"] + s["resources"])),
            "log": [{"at": fmt_dt(d.at), "request_id": d.request_id, "school": d.school_name, "user": d.user_name,
                     "kind": d.kind, "item": d.item, "file": d.file_name} for d in log]}
