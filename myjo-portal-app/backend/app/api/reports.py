"""17 reports with common filters; export to Excel (xlsx), PDF and CSV."""
import csv
import io
from datetime import date
from flask import Blueprint, request, send_file
from .. import constants as C
from ..extensions import db
from ..models import DemoRequest, Download, FollowUp, QuestionPaper, Resource, Training
from ..security import login_required, require_screen
from ..util import ApiError, human_d, human_dt
from .academic import res_audience

bp = Blueprint("reports", __name__)
N = "number"


def L(xs):
    return ", ".join(xs or []) or "—"


def flt():
    a = request.args
    f = {k: a.get(k) for k in ("from", "to", "school", "distributor", "city", "state", "ay", "series", "cls", "subject",
                               "status", "employee", "marketing", "presenter", "trainer") if a.get(k)}
    for k in ("from", "to"):
        if k in f:
            try:
                f[k] = date.fromisoformat(f[k])
            except ValueError:
                raise ApiError("Dates must be YYYY-MM-DD.", field=k)
    return f


def match(fac, f):
    for k, v in f.items():
        if k in ("from", "to"):
            d = fac.get("date")
            if not d or (k == "from" and d < v) or (k == "to" and d > v):
                return False
            continue
        if k not in fac:
            continue
        vals = [str(x) for x in (fac[k] if isinstance(fac[k], (list, tuple)) else [fac[k]]) if x is not None]
        if str(v) not in vals:
            return False
    return True


def fac_school(r):
    return {"school": r.id, "distributor": r.distributor_id, "city": r.school.city, "state": r.school.state}


def fac_req(r):
    tr = [t.trainer for t in Training.query.join(Training.schools).filter_by(request_id=r.id)]
    return {**fac_school(r), "date": r.created_at.date(), "ay": [r.ay, r.order.ay if r.order else None],
            "series": r.series + (r.order.series if r.order else []), "cls": r.classes, "subject": r.subjects,
            "status": [r.status, r.order_status],
            "employee": [r.assigned_to, r.schedule and r.schedule.presenter, r.schedule and r.schedule.marketing, r.marketing and r.marketing.person],
            "marketing": [r.schedule and r.schedule.marketing, r.marketing and r.marketing.person],
            "presenter": [r.schedule and r.schedule.presenter], "trainer": tr}


def reqs(f):
    return [r for r in DemoRequest.query.filter_by(cancelled=False).order_by(DemoRequest.created_at.desc()) if match(fac_req(r), f)]


def conv(rs):
    return [r for r in rs if r.status == "Converted"]


def books(rs):
    return sum(r.order.qty for r in conv(rs) if r.order)


def pct(a, b):
    return f"{round(a * 1000 / b) / 10}%" if b else "—"


def group(rs, key):
    out = {}
    for r in rs:
        for k in (key(r) if isinstance(key(r), list) else [key(r)]):
            out.setdefault(k, []).append(r)
    return sorted(out.items(), key=lambda kv: str(kv[0]))


def demos(rs):
    return [r for r in rs if r.feedback]


def won_after_demo(rs):
    return [r for r in demos(rs) if r.status == "Converted"]


def r_requests(f):
    return [("Request no.", 0), ("Date", 0), ("School", 0), ("City", 0), ("State", 0), ("Board", 0), ("AY", 0), ("Distributor", 0),
            ("Series", 0), ("Classes", 0), ("Exp. qty", N), ("Status", 0)], [
        [r.no, human_d(r.created_at), r.school.name, r.school.city, r.school.state, r.school.board, r.ay, r.distributor.org,
         L(r.series), L(r.classes), r.exp_qty or 0, r.status] for r in reqs(f)], False


def r_scheduled(f):
    return [("Request no.", 0), ("School", 0), ("City", 0), ("Distributor", 0), ("Demo date & time", 0), ("Mode", 0), ("Link / venue", 0),
            ("Presenter", 0), ("Marketing", 0), ("Shared on", 0), ("Status", 0)], [
        [r.no, r.school.name, r.school.city, r.distributor.org, human_dt(r.schedule.at), r.schedule.mode + (f" · {r.schedule.platform}" if r.schedule.platform else ""),
         r.schedule.link or r.schedule.venue, r.schedule.presenter, r.schedule.marketing, human_dt(r.schedule.shared_at) if r.schedule.shared_at else "Not shared", r.status]
        for r in reqs(f) if r.schedule], False


def r_completed(f):
    return [("Request no.", 0), ("School", 0), ("Demo date", 0), ("Conducted by", 0), ("Attendees", 0), ("Series demonstrated", 0),
            ("Interest", 0), ("Competitor", 0), ("Next follow-up", 0)], [
        [r.no, r.school.name, human_d(r.feedback.date), r.feedback.by, r.feedback.attendees, L(r.feedback.series), r.feedback.interest,
         r.feedback.competitor or "", human_d(r.feedback.next_follow)] for r in reqs(f) if r.feedback], False


def r_pending_fb(f):
    from ..util import now
    nl = now()
    return [("Request no.", 0), ("School", 0), ("Demo date & time", 0), ("Presenter", 0), ("Days pending", N)], [
        [r.no, r.school.name, human_dt(r.schedule.at), r.schedule.presenter, (nl.date() - r.schedule.at.date()).days]
        for r in reqs(f) if r.status == "Demo Scheduled" and r.schedule and r.schedule.at < nl], False


def r_followups(f):
    rows = []
    for x in FollowUp.query.order_by(FollowUp.at.desc(), FollowUp.id.desc()):
        r = db.session.get(DemoRequest, x.request_id)
        if r.cancelled or not match({**fac_req(r), "date": x.at.date(), "employee": [x.by], "marketing": [x.by]}, f):
            continue
        rows.append([human_dt(x.at), r.school.name, x.method, x.person, x.summary, x.next_action or "", human_d(x.next_date), x.by])
    return [("Date & time", 0), ("School", 0), ("Method", 0), ("Person contacted", 0), ("Summary", 0), ("Next action", 0), ("Next date", 0), ("Updated by", 0)], rows, False


def r_converted(f):
    return [("School", 0), ("City", 0), ("State", 0), ("Distributor", 0), ("AY", 0), ("Series", 0), ("Qty", N), ("PO / ref", 0),
            ("Confirmed", 0), ("Payment", 0), ("Source", 0)], [
        [r.school.name, r.school.city, r.school.state, r.distributor.org, r.order.ay, L(r.order.series), r.order.qty, r.order.po,
         human_d(r.order.conf_date), r.order.payment, "Distributor" if r.order.source == "distributor" else "Myjo"]
        for r in conv(reqs(f)) if r.order], True


def r_lost(f):
    return [("School", 0), ("City", 0), ("Distributor", 0), ("Order status", 0), ("Competitor", 0), ("Interest", 0), ("Remarks", 0)], [
        [r.school.name, r.school.city, r.distributor.org, r.order_status or "", (r.marketing and r.marketing.competitor) or (r.feedback and r.feedback.competitor) or "",
         r.feedback.interest if r.feedback else "", (r.marketing and r.marketing.remarks) or ""]
        for r in reqs(f) if r.status == "Not Converted" or r.order_status in C.LOST], False


def r_distributor(f):
    rows = [[k, len(rs), len(demos(rs)), len(won_after_demo(rs)), len([r for r in conv(rs) if not r.feedback]),
             sum(r.status == "Not Converted" for r in rs), books(rs), pct(len(won_after_demo(rs)), len(demos(rs)))]
            for k, rs in group(reqs(f), lambda r: r.distributor.org)]
    return [("Distributor", 0), ("Requests", N), ("Demos completed", N), ("Converted after demo", N), ("Direct orders", N),
            ("Lost", N), ("Books ordered", N), ("Demo-to-order %", 0)], rows, True


def r_geo(f):
    rows = [[*k.split("|"), len(rs), len(demos(rs)), len(conv(rs)), books(rs)] for k, rs in group(reqs(f), lambda r: f"{r.school.state}|{r.school.city}")]
    return [("State", 0), ("City", 0), ("Requests", N), ("Demos completed", N), ("Converted", N), ("Books ordered", N)], rows, True


def r_series(f):
    from ..models import Series
    rs = reqs(f)
    rows = []
    for s in [x.name for x in Series.query.order_by(Series.id)]:
        if f.get("series") and f["series"] != s:
            continue
        i = [r for r in rs if s in r.series]
        d = [r for r in rs if r.feedback and s in (r.feedback.series or [])]
        o = [r for r in rs if r.status == "Converted" and r.order and s in r.order.series]
        rows.append([s, len(i), len(d), len(o), pct(len([r for r in o if r.feedback]), len(d))])
    return [("Book series", 0), ("Schools interested", N), ("Demonstrated", N), ("Ordered", N), ("Conversion after demo %", 0)], rows, False


def r_monthly(f):
    rows = [[date.fromisoformat(k + "-01").strftime("%b %Y"), len(rs), len(demos(rs)), len(won_after_demo(rs)),
             pct(len(won_after_demo(rs)), len(demos(rs))), books(rs)] for k, rs in group(reqs(f), lambda r: r.created_at.strftime("%Y-%m"))]
    return [("Month of request", 0), ("Requests", N), ("Demos completed", N), ("Converted after demo", N), ("Conversion %", 0), ("Books ordered", N)], rows, True


def r_order_qty(f):
    return [("School", 0), ("AY", 0), ("Distributor", 0), ("Series", 0), ("Classes", 0), ("Subjects", 0), ("Qty", N), ("PO / ref", 0),
            ("Confirmed", 0), ("Delivery", 0), ("Payment", 0)], [
        [r.school.name, r.order.ay, r.distributor.org, L(r.order.series), L(r.order.classes), L(r.order.subjects), r.order.qty, r.order.po,
         human_d(r.order.conf_date), human_d(r.order.del_date), r.order.payment] for r in conv(reqs(f)) if r.order], True


def fac_tr(t, s):
    r = s.request
    return {**fac_school(r), "date": t.at.date(), "ay": [t.ay], "series": t.series, "cls": t.classes, "subject": t.subjects,
            "status": [t.status], "employee": [t.trainer], "trainer": [t.trainer]}


def r_training(f):
    rows = []
    for t in Training.query.filter_by(cancelled=False).order_by(Training.at.desc()):
        for s in t.schools:
            if not match(fac_tr(t, s), f):
                continue
            rows.append([t.no, t.title, t.type, s.request.school.name, L(t.series), t.mode, human_dt(t.at), t.trainer, s.expected,
                         (s.school_confirm or "Awaiting") + (f" ({s.school_teachers})" if s.school_teachers is not None else ""),
                         s.attended or 0, s.attendance or "—", t.status, f"{s.fb_rating} / 5" if s.fb_rating else "—", s.fb_text or "", s.myjo_feedback or ""])
    return [("No.", 0), ("Session", 0), ("Type", 0), ("School", 0), ("Series", 0), ("Mode", 0), ("Date & time", 0), ("Trainer", 0),
            ("Expected", N), ("School confirmed", 0), ("Attended", N), ("Attendance", 0), ("Status", 0), ("School rating", 0),
            ("School feedback", 0), ("Myjo feedback", 0)], rows, True


def fac_qp(p):
    return {**fac_school(p.request), "date": p.due_date, "ay": [p.ay], "series": [p.series], "cls": [p.cls], "subject": [p.subject],
            "status": [p.status], "employee": [p.assignee]}


def r_papers(f):
    return [("No.", 0), ("School", 0), ("AY", 0), ("Class", 0), ("Subject", 0), ("Series", 0), ("Exam", 0), ("Due", 0), ("Assigned", 0),
            ("Max marks", N), ("Delivered", 0), ("Status", 0)], [
        [p.no, p.request.school.name, p.ay, p.cls, p.subject, p.series, p.exam, human_d(p.due_date), p.assignee or "", p.max_marks or 0,
         human_d(p.delivery_date), p.status] for p in QuestionPaper.query.filter_by(cancelled=False).order_by(QuestionPaper.due_date) if match(fac_qp(p), f)], False


def r_paper_dl(f):
    return [("No.", 0), ("School", 0), ("Class · subject", 0), ("Exam", 0), ("QP file", 0), ("Answer key", 0), ("Status", 0), ("Published", 0), ("Downloads", N)], [
        [p.no, p.request.school.name, f"Class {p.cls} {p.subject}", p.exam, p.qp_file.name if p.qp_file else "—", p.ak_file.name if p.ak_file else "—",
         p.status, human_dt(p.published_at) if p.published_at else "—", Download.query.filter_by(item_ref=p.no).count()]
        for p in QuestionPaper.query.filter_by(cancelled=False) if match(fac_qp(p), f)], True


def r_manuals(f):
    rows = []
    for x in Resource.query.filter_by(cancelled=False).order_by(Resource.upload_date.desc()):
        fac = {"date": x.upload_date, "ay": [x.ay], "series": [x.series], "cls": [x.cls], "subject": [x.subject], "status": [x.status],
               "employee": [x.uploaded_by], "school": res_audience(x)}
        if not match(fac, f):
            continue
        q = Download.query.filter_by(item_ref=x.no)
        if f.get("school"):
            q = q.filter_by(request_id=int(f["school"]))
        rows.append([x.no, x.title, x.type, x.series, f"{x.cls} · {x.subject}", x.version, human_d(x.upload_date), x.uploaded_by, x.access, x.status, q.count()])
    return [("No.", 0), ("Title", 0), ("Type", 0), ("Series", 0), ("Class · subject", 0), ("Version", 0), ("Uploaded", 0), ("By", 0),
            ("Access", 0), ("Status", 0), ("Downloads", N)], rows, True


def r_overdue(f):
    from ..util import now, today
    nl, td = now(), today()
    rows = []
    for t in Training.query.filter(Training.cancelled.is_(False), Training.status.in_(["Draft", "Scheduled"])):
        if any(match(fac_tr(t, s), f) for s in t.schools):
            late = t.status == "Scheduled" and t.at < nl
            rows.append(["Group training", t.no, "; ".join(s.request.school.name for s in t.schools), t.title, human_dt(t.at), t.trainer,
                         "Completion not recorded" if late else t.status, (td - t.at.date()).days if late else 0])
    for p in QuestionPaper.query.filter(QuestionPaper.cancelled.is_(False), QuestionPaper.status.notin_(list(C.PAPER_LIVE) + ["Closed"])):
        if match(fac_qp(p), f):
            rows.append(["Question paper", p.no, p.request.school.name, f"Class {p.cls} {p.subject} · {p.exam}", human_d(p.due_date),
                         p.assignee or "Unassigned", p.status, (td - p.due_date).days if p.due_date < td else 0])
    rows.sort(key=lambda r: -r[7])
    return [("Type", 0), ("Ref", 0), ("School", 0), ("Item", 0), ("Due", 0), ("Assigned", 0), ("Status", 0), ("Days overdue", N)], rows, False


REPORTS = [("requests", "Demo request report", r_requests), ("scheduled", "Demo scheduled report", r_scheduled),
           ("completed", "Demo completion report", r_completed), ("pending-feedback", "Pending Myjo feedback report", r_pending_fb),
           ("followups", "Marketing follow-up report", r_followups), ("converted", "Converted school report", r_converted),
           ("lost", "Lost school report", r_lost), ("distributor", "Distributor-wise performance report", r_distributor),
           ("geo", "City-wise and state-wise report", r_geo), ("series", "Book-series-wise interest and conversion report", r_series),
           ("monthly", "Month-wise demo-to-order conversion report", r_monthly), ("order-qty", "Confirmed order quantity report", r_order_qty),
           ("training", "Teacher-training report (school-wise)", r_training), ("papers", "Question-paper support report", r_papers),
           ("paper-downloads", "Question-paper upload and download report", r_paper_dl),
           ("manuals", "Teacher-training manual upload and download report", r_manuals),
           ("overdue", "Pending and overdue support report", r_overdue)]
BY_KEY = {k: (n, fn) for k, n, fn in REPORTS}


def run(key):
    require_screen("reports")
    if key not in BY_KEY:
        raise ApiError("Unknown report.", 404)
    name, fn = BY_KEY[key]
    cols, rows, with_total = fn(flt())
    total = None
    if with_total and rows:
        total = ["Total"] + [sum(r[i] for r in rows) if t == N and all(isinstance(r[i], (int, float)) for r in rows) else "" for i, (_, t) in enumerate(cols)][1:]
    return name, [{"label": l, "type": "number" if t == N else "text"} for l, t in cols], rows, total


@bp.get("/reports")
@login_required
def list_reports():
    require_screen("reports")
    return {"items": [{"key": k, "name": n} for k, n, _ in REPORTS]}


@bp.get("/reports/<key>")
@login_required
def report(key):
    name, cols, rows, total = run(key)
    return {"name": name, "columns": cols, "rows": rows, "total": total}


@bp.get("/reports/<key>/export")
@login_required
def export(key):
    name, cols, rows, total = run(key)
    fmt = request.args.get("format", "xlsx")
    data = rows + ([total] if total else [])
    fname = name.replace(" ", "-").lower()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow([c["label"] for c in cols])
        w.writerows(data)
        return send_file(io.BytesIO(buf.getvalue().encode("utf-8-sig")), mimetype="text/csv", as_attachment=True, download_name=f"{fname}.csv")
    if fmt == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        wb = Workbook()
        ws = wb.active
        ws.title = "Report"
        ws.append([name])
        ws["A1"].font = Font(bold=True, size=13)
        ws.append([c["label"] for c in cols])
        for c in ws[2]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="D9181F")
        for r in data:
            ws.append(r)
        if total:
            for c in ws[ws.max_row]:
                c.font = Font(bold=True)
        for i, col in enumerate(ws.columns, 1):
            ws.column_dimensions[col[1].column_letter].width = min(45, max(10, max(len(str(c.value or "")) for c in col[1:]) + 2))
        ws.freeze_panes = "A3"
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=f"{fname}.xlsx")
    if fmt == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        out = io.BytesIO()
        doc = SimpleDocTemplate(out, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24, title=name)
        st = getSampleStyleSheet()
        cell = st["BodyText"].clone("cell", fontSize=7.5, leading=9)
        head = cell.clone("head", textColor=colors.white, fontName="Helvetica-Bold")
        tbl = [[Paragraph(c["label"], head) for c in cols]] + [[Paragraph(str(v if v is not None else ""), cell) for v in r] for r in data]
        t = Table(tbl, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9181F")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E6E0E0")),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAF8F8")])]))
        doc.build([Paragraph(f"Myjo Publications · {name}", st["Title"]), Spacer(1, 6), t])
        out.seek(0)
        return send_file(out, mimetype="application/pdf", as_attachment=True, download_name=f"{fname}.pdf")
    raise ApiError("Format must be xlsx, pdf or csv.", field="format")
