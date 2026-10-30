"""Role-aware dashboard and global search."""
from datetime import timedelta
from flask import Blueprint, g, request
from sqlalchemy import func, or_
from .. import constants as C
from ..models import DemoRequest, Download, QuestionPaper, Resource, School, Training, Order, DistOrder
from ..security import can, login_required
from ..services.academic import coverage, eligible_requests
from ..util import ApiError, fmt_d, fmt_dt, human_dt, now, today
from .requests_api import is_final, list_json, visible_query
from .admin import pending_cancellations

bp = Blueprint("dashboard", __name__)


def item(date, title, subtitle, screen, id=None, late=False):
    return {"date": date, "title": title, "subtitle": subtitle, "link": {"screen": screen, "id": id}, "late": late}


def kpi(group, label, value, link, tone=None):
    return {"group": group, "label": label, "value": value, "link": link, "tone": tone}


def conversion(rows):
    """Demo-to-order conversion counts only schools that had a demo (direct orders are reported separately)."""
    demos = [r for r in rows if r.feedback]
    won = [r for r in demos if r.status == "Converted"]
    return (round(len(won) * 100 / len(demos)) if demos else 0), len(won), len(demos)


@bp.get("/nav-counts")
@login_required
def nav_counts():
    """Small numbers beside menu items: things waiting for this user's attention. Zero counts are left out."""
    from ..security import screens_for
    u, nl, td = g.user, now(), today()
    if u.role == "school":
        return {"counts": {}}
    screens = set(screens_for(u))
    rows = [r for r in visible_query().all() if not r.cancelled]
    c = {}
    if "requests" in screens:
        c["requests"] = sum(r.status == "New" for r in rows)
    if "marketing" in screens:
        c["marketing"] = sum(bool(r.marketing and r.marketing.next_follow and r.marketing.next_follow < td and not is_final(r)) for r in rows)
    if "myorders" in screens:
        c["myorders"] = sum(bool(r.dist_order and r.dist_order.status == "Returned") for r in rows)
    if "orders" in screens and can("order"):
        c["orders"] = sum(bool(r.dist_order and r.dist_order.status == "Submitted") for r in rows)
    if "training" in screens:
        c["training"] = Training.query.filter(Training.cancelled.is_(False), Training.status == "Scheduled", Training.at < nl).count()
    if "papers" in screens:
        c["papers"] = QuestionPaper.query.filter_by(cancelled=False, status="New").count()
    if "acschools" in screens and can("academic"):
        c["acschools"] = sum(not coverage(r)["complete"] for r in eligible_requests())
    return {"counts": {k: v for k, v in c.items() if v}}


@bp.get("/dashboard")
@login_required
def dashboard():
    u, nl, td = g.user, now(), today()
    if u.role == "school":
        raise ApiError("Use the school portal.", 403)
    rows = [r for r in visible_query().all() if not r.cancelled]
    conv = [r for r in rows if r.status == "Converted"]
    books = sum(r.order.qty for r in conv if r.order)
    pct, won, demos = conversion(rows)
    out = {"kpis": [], "overdue": [], "upcoming": [], "my_work": [], "downloads_by_school": [], "funnel": [],
           "no_download_schools": [], "pending_cancellations": []}
    if u.role == "dist":
        out["kpis"] = [kpi("My schools", "Demo requests", len(rows), "requests"),
                       kpi("My schools", "Awaiting review", sum(r.status in ("New", "Under Review") for r in rows), "requests"),
                       kpi("My schools", "Demos scheduled", sum(r.status == "Demo Scheduled" for r in rows), "requests"),
                       kpi("My schools", "Orders waiting for Myjo", sum(bool(r.dist_order and r.dist_order.status == "Submitted") for r in rows), "myorders"),
                       kpi("My schools", "Converted schools", len(conv), "requests", "good"),
                       kpi("My schools", "Books ordered", books, "myorders")]
        out["upcoming"] = [item(fmt_dt(r.schedule.at), "Demo · " + r.school.name, r.schedule.mode + " · " + r.schedule.presenter, "req", r.id)
                           for r in rows if r.status == "Demo Scheduled" and r.schedule and r.schedule.at >= nl]
        return out
    trs = [t for t in Training.query.filter_by(cancelled=False).all()]
    papers = QuestionPaper.query.filter_by(cancelled=False).all()
    res = Resource.query.filter_by(cancelled=False).all()
    el = eligible_requests()
    missing = [r for r in el if not coverage(r)["complete"]]
    pend_fb = [r for r in rows if r.status == "Demo Scheduled" and r.schedule and r.schedule.at < nl]
    fu_over = [r for r in rows if r.marketing and r.marketing.next_follow and r.marketing.next_follow < td and not is_final(r)]
    tr_over = [t for t in trs if t.status == "Scheduled" and t.at < nl]
    qp_open = [p for p in papers if p.status not in C.PAPER_LIVE + ("Closed",)]
    qp_over = [p for p in qp_open if p.due_date < td]
    discussing = [r for r in rows if not is_final(r) and (r.order_status in ("Quotation Sent", "Sample Sent", "Under Discussion", "On Hold") or r.status == "Follow-up Pending")]
    pending_dist = [r for r in rows if r.dist_order and r.dist_order.status == "Submitted"]
    direct = [r for r in conv if not r.feedback]
    G1, G2, G3 = "Demo pipeline", "Conversion", "Academic support"
    out["kpis"] = [
        kpi(G1, "Total demo requests", len(rows), "requests"), kpi(G1, "New demo requests", sum(r.status == "New" for r in rows), "requests"),
        kpi(G1, "Demos scheduled", sum(r.status == "Demo Scheduled" for r in rows), "requests"),
        kpi(G1, "Demos completed", demos, "requests"), kpi(G1, "Pending Myjo feedback", len(pend_fb), "requests", "alert" if pend_fb else None),
        kpi(G1, "Pending marketing follow-ups", sum(r.status in ("Demo Completed", "Follow-up Pending") for r in rows), "marketing"),
        kpi(G2, "Converted schools", len(conv), "orders", "good"),
        kpi(G2, "Distributor orders to review", len(pending_dist), "orders", "alert" if pending_dist else None),
        kpi(G2, "Direct distributor orders (no demo)", len(direct), "orders"),
        kpi(G2, "Schools under discussion", len(discussing), "marketing"),
        kpi(G2, "Lost schools", sum(r.status == "Not Converted" for r in rows), "reports"),
        kpi(G2, "Confirmed books ordered", books, "orders"),
        kpi(G2, "Demo-to-order conversion", f"{pct}%", "reports"),
        kpi(G3, "Orders missing academic support", f"{len(missing)} / {len(el)}", "acschools", "alert" if missing else None),
        kpi(G3, "Draft & scheduled training sessions", sum(t.status in ("Draft", "Scheduled") for t in trs), "training"),
        kpi(G3, "Pending question-paper requests", len(qp_open), "papers"),
        kpi(G3, "Published question papers", sum(p.status in C.PAPER_LIVE for p in papers), "papers"),
        kpi(G3, "Training manuals / all resources", f"{sum(x.type == 'Teacher training manual' for x in res)} / {len(res)}", "resources"),
        kpi(G3, "Overdue follow-ups & tasks", len(pend_fb) + len(fu_over) + len(tr_over) + len(qp_over), "dashboard",
            "alert" if (pend_fb or fu_over or tr_over or qp_over) else None)]
    ov = [item(fmt_d(r.schedule.at.date()), "Demo feedback pending", f"{r.school.name} · presenter {r.schedule.presenter}", "req", r.id, True) for r in pend_fb]
    ov += [item(fmt_d(r.marketing.next_follow), "Follow-up overdue", f"{r.school.name} · {r.marketing.next_action or ''} · {r.marketing.person}", "req", r.id, True) for r in fu_over]
    ov += [item(fmt_d(t.at.date()), f"Training completion not recorded · {t.no}", f"{t.title} · {t.trainer}", "trs", t.id, True) for t in tr_over]
    ov += [item(fmt_d(p.due_date), f"Question paper overdue · {p.no}", f"{p.request.school.name} · Class {p.cls} {p.subject} · {p.assignee or 'unassigned'}", "papers", None, True) for p in qp_over]
    out["overdue"] = sorted(ov, key=lambda x: x["date"])
    lim = nl + timedelta(days=21)
    up = [item(fmt_dt(r.schedule.at), "Demo · " + r.school.name, f"{r.schedule.mode} · {r.schedule.presenter}", "req", r.id)
          for r in rows if r.status == "Demo Scheduled" and r.schedule and nl <= r.schedule.at <= lim]
    up += [item(fmt_d(r.marketing.next_follow), "Follow-up · " + r.school.name, f"{r.marketing.next_action or ''} · {r.marketing.person}", "req", r.id)
           for r in rows if r.marketing and r.marketing.next_follow and td <= r.marketing.next_follow <= lim.date() and not is_final(r)]
    up += [item(fmt_dt(t.at), "Group training · " + t.title, f"{t.mode} · {t.trainer}", "trs", t.id) for t in trs if t.status == "Scheduled" and nl <= t.at <= lim]
    up += [item(fmt_d(p.due_date), f"Question paper due · {p.no}", f"{p.request.school.name} · Class {p.cls} {p.subject}", "papers")
           for p in qp_open if td <= p.due_date <= lim.date()]
    out["upcoming"] = sorted(up, key=lambda x: x["date"])
    out["my_work"] = my_work(rows, trs, papers, res, el)
    stats = []
    for r in el:
        ds = Download.query.filter_by(request_id=r.id).all()
        stats.append({"request_id": r.id, "school": r.school.name, "papers": sum(d.kind != "Resource" for d in ds),
                      "resources": sum(d.kind == "Resource" for d in ds), "last": fmt_dt(max((d.at for d in ds), default=None))})
    out["downloads_by_school"] = sorted(stats, key=lambda s: -(s["papers"] + s["resources"]))
    out["no_download_schools"] = [s["school"] for s in stats if not s["papers"] and not s["resources"]]
    out["funnel"] = [{"label": "Requests", "value": len(rows)},
                     {"label": "Approved", "value": sum(r.status not in ("New", "Under Review", "On Hold", "Rejected") and not r.direct for r in rows)},
                     {"label": "Demo scheduled", "value": sum(bool(r.schedule) for r in rows)},
                     {"label": "Demo completed", "value": demos}, {"label": "Converted after demo", "value": won}]
    if can("approveCancel"):
        out["pending_cancellations"] = pending_cancellations()
    return out


def my_work(rows, trs, papers, res, el):
    u, n, nl, td = g.user, g.user.name, now(), today()
    groups = []

    def grp(title, items):
        if items:
            groups.append({"title": title, "items": items})
    if u.role == "demo":
        mine = lambda r: r.assigned_to in (None, n)  # noqa: E731
        grp("Requests to review", [item(fmt_dt(r.created_at), r.school.name, f"{r.no} · {r.status}", "req", r.id) for r in rows if r.status in ("New", "Under Review") and mine(r)])
        grp("Approved, demo to schedule", [item(fmt_d(r.pref_date), r.school.name, f"Preferred {fmt_d(r.pref_date)} {r.pref_time or ''}", "req", r.id) for r in rows if r.status == "Approved" and mine(r)])
        grp("Demo feedback overdue", [item(fmt_d(r.schedule.at.date()), r.school.name, f"Demo was {human_dt(r.schedule.at)}", "req", r.id, True)
                                      for r in rows if r.status == "Demo Scheduled" and r.schedule and r.schedule.at < nl and r.schedule.presenter == n])
        grp("My upcoming demos", [item(fmt_dt(r.schedule.at), r.school.name, r.schedule.mode + ("" if r.schedule.shared_at else " · details not shared yet"), "req", r.id)
                                  for r in rows if r.status == "Demo Scheduled" and r.schedule and r.schedule.at >= nl and r.schedule.presenter == n])
    elif u.role == "mkt":
        mine = lambda r: not is_final(r) and ((r.marketing and r.marketing.person == n) or (not r.marketing and r.schedule and r.schedule.marketing == n))  # noqa: E731
        grp("Distributor orders to review", [item(fmt_dt(r.dist_order.at), r.school.name, f"{r.dist_order.po} · {r.dist_order.qty} books", "req", r.id)
                                             for r in rows if r.dist_order and r.dist_order.status == "Submitted"])
        grp("Follow-ups overdue", [item(fmt_d(r.marketing.next_follow), r.school.name, r.marketing.next_action or "Follow up", "req", r.id, True)
                                   for r in rows if mine(r) and r.marketing and r.marketing.next_follow and r.marketing.next_follow < td])
        grp("Follow-ups due in 7 days", [item(fmt_d(r.marketing.next_follow), r.school.name, r.marketing.next_action or "Follow up", "req", r.id)
                                         for r in rows if mine(r) and r.marketing and r.marketing.next_follow and td <= r.marketing.next_follow <= td + timedelta(days=7)])
        grp("Demo done, marketing feedback needed", [item(fmt_d(r.feedback.date), r.school.name, "Interest " + r.feedback.interest, "req", r.id)
                                                     for r in rows if r.status == "Demo Completed" and not r.marketing and r.schedule and r.schedule.marketing == n and r.feedback])
    elif u.role == "acad":
        grp("Orders missing academic support", [item(fmt_d((r.order.conf_date if r.order else r.dist_order.at.date())), r.school.name,
                                                     "Needs " + ", ".join(coverage(r)["missing"]), "acschools") for r in el if not coverage(r)["complete"]])
        grp("Training completion to record", [item(fmt_d(t.at.date()), t.title, f"{len(t.schools)} school(s)", "trs", t.id, True) for t in trs if t.status == "Scheduled" and t.at < nl and t.trainer == n])
        grp("My upcoming training sessions", [item(fmt_dt(t.at), t.title, "; ".join(s.request.school.name for s in t.schools), "trs", t.id) for t in trs if t.status == "Scheduled" and t.at >= nl and t.trainer == n])
        grp("Draft sessions", [item(fmt_dt(t.at), t.title, "Not visible to schools until scheduled", "trs", t.id) for t in trs if t.status == "Draft" and t.trainer == n])
        open_p = [p for p in papers if p.status not in C.PAPER_LIVE + ("Closed",) and p.assignee in (None, n)]
        grp("Question papers overdue", [item(fmt_d(p.due_date), f"{p.no} · {p.request.school.name}", f"Class {p.cls} {p.subject} · {p.status}", "papers", None, True) for p in open_p if p.due_date < td])
        grp("Question papers to prepare", [item(fmt_d(p.due_date), f"{p.no} · {p.request.school.name}", f"Class {p.cls} {p.subject} · {p.status}", "papers") for p in open_p if p.due_date >= td])
        grp("My draft resources", [item(fmt_d(x.upload_date), x.title, "Publish to make it visible to schools", "resources") for x in res if x.status == "Draft" and x.uploaded_by == n])
    return groups


@bp.get("/search")
@login_required
def search():
    if g.user.role == "school":
        raise ApiError("Not available for school users.", 403)
    t = (request.args.get("q") or "").strip().lower()
    if not t:
        return {"requests": [], "trainings": [], "papers": [], "resources": []}
    like = f"%{t}%"
    q = (visible_query().join(School, DemoRequest.school_id == School.id)
         .outerjoin(Order, Order.request_id == DemoRequest.id).outerjoin(DistOrder, DistOrder.request_id == DemoRequest.id))
    reqs = q.filter(or_(func.lower(School.name).like(like), func.lower(School.city).like(like), School.mobile.like(like),
                        func.lower(DemoRequest.no).like(like), func.lower(Order.po).like(like), func.lower(DistOrder.po).like(like),
                        func.lower(School.contact).like(like), func.lower(School.email).like(like))).all()
    reqs += [r for r in visible_query().all() if r not in reqs and (any(t in s.lower() for s in r.series)
                                                                  or t in (r.distributor.org or "").lower())]
    out = {"requests": [list_json(r) for r in reqs], "trainings": [], "papers": [], "resources": []}
    if g.user.role != "dist":
        out["trainings"] = [{"id": x.id, "no": x.no, "title": x.title, "status": x.status, "schools": "; ".join(s.request.school.name for s in x.schools)}
                            for x in Training.query.all() if t in f"{x.no} {x.title} {x.type} {' '.join(x.series)} {' '.join(s.request.school.name for s in x.schools)}".lower()]
        out["papers"] = [{"id": p.id, "no": p.no, "school": p.request.school.name, "cls": p.cls, "subject": p.subject, "status": p.status}
                         for p in QuestionPaper.query.all() if t in f"{p.no} {p.series} {p.subject} {p.request.school.name}".lower()]
        out["resources"] = [{"id": x.id, "no": x.no, "title": x.title, "type": x.type, "series": x.series, "status": x.status}
                            for x in Resource.query.all() if t in f"{x.no} {x.title} {x.series} {x.type}".lower()]
    return out
