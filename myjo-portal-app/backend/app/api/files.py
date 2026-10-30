"""File upload and access-checked download (downloads by school users are recorded)."""
import os
import uuid
from flask import Blueprint, current_app, g, request, send_file
from ..extensions import db
from ..models import Download, File, QuestionPaper, Resource
from ..security import login_required
from ..util import ApiError, now
from ..services.audit import audit

bp = Blueprint("files", __name__)
ALLOWED = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "zip", "jpg", "jpeg", "png"}


def file_json(f):
    return {"id": f.id, "name": f.name, "size": f.size, "mime": f.mime} if f else None


@bp.post("/files")
@login_required
def upload():
    if g.user.role == "school":
        raise ApiError("School users cannot upload files.", 403)
    up = request.files.get("file")
    if not up or not up.filename:
        raise ApiError("Choose a file to upload.", field="file")
    ext = up.filename.rsplit(".", 1)[-1].lower() if "." in up.filename else ""
    if ext not in ALLOWED:
        raise ApiError("Only PDF, Word, PowerPoint, Excel, ZIP and image files are allowed.", field="file")
    stored = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_DIR"], stored)
    up.save(path)
    f = File(name=os.path.basename(up.filename)[:255], stored=stored, mime=up.mimetype or "application/octet-stream",
             size=os.path.getsize(path), uploaded_by=g.user.id, at=now())
    db.session.add(f)
    db.session.commit()
    return file_json(f), 201


@bp.get("/files/<int:fid>/download")
@login_required
def download(fid):
    f = db.session.get(File, fid)
    if not f:
        raise ApiError("File not found.", 404)
    u = g.user
    if u.role == "school":
        from ..services.academic import academic_eligible, visible_resources_for
        from ..models import DemoRequest, PaperRevocation
        r = db.session.get(DemoRequest, u.school_request_id)
        ctx = (request.args.get("context") or "").split(":")
        if not r or not academic_eligible(r):
            raise ApiError("Your school's portal is not available.", 403)
        if ctx[0] == "paper" and len(ctx) == 3:
            p = db.session.get(QuestionPaper, int(ctx[1]))
            ok = (p and p.request_id == r.id and p.status in ("Published", "Delivered") and not p.cancelled
                  and not db.session.get(PaperRevocation, (p.id, r.id))
                  and ((ctx[2] == "qp" and p.qp_file_id == fid) or (ctx[2] == "ak" and p.ak_file_id == fid)))
            if not ok:
                raise ApiError("This paper is no longer available to your school.", 403)
            kind, item, ref = ("Question paper" if ctx[2] == "qp" else "Answer key"), f"{p.no} · Class {p.cls} {p.subject} · {p.exam}", p.no
        elif ctx[0] == "resource" and len(ctx) == 2:
            res = db.session.get(Resource, int(ctx[1]))
            if not res or res.file_id != fid or res.id not in {x.id for x in visible_resources_for(r)}:
                raise ApiError("This resource is no longer available to your school.", 403)
            kind, item, ref = "Resource", res.title, res.no
        else:
            raise ApiError("Download not allowed.", 403)
        db.session.add(Download(at=now(), request_id=r.id, user_id=u.id, user_name=u.name, school_name=r.school.name,
                                kind=kind, item_ref=ref, item=item, file_name=f.name))
        audit("Download", ref, "Downloaded", None, f"{kind} · {f.name} · {r.school.name}", "download")
        db.session.commit()
    elif u.role == "dist":
        raise ApiError("Download not allowed.", 403)
    path = os.path.join(current_app.config["UPLOAD_DIR"], f.stored)
    if not os.path.exists(path):
        raise ApiError("The stored file is missing. Ask the Academic team to upload it again.", 404)
    return send_file(path, mimetype=f.mime, as_attachment=True, download_name=f.name)


def record_link_view(r, res):
    """Video links are not files; opening one is still recorded."""
    u = g.user
    db.session.add(Download(at=now(), request_id=r.id, user_id=u.id, user_name=u.name, school_name=r.school.name,
                            kind="Resource", item_ref=res.no, item=res.title, file_name=res.link or ""))
    audit("Download", res.no, "Opened link", None, f"{res.title} · {r.school.name}", "download")
