"""Notifications: every message is stored in `notifications`; when SEND_MESSAGES=1 it is also
sent by email (SMTP) and WhatsApp (Meta WhatsApp Cloud API)."""
import json
import smtplib
import urllib.request
from email.message import EmailMessage
from flask import current_app
from ..extensions import db
from ..models import DemoRequest, Notification, User
from ..util import now


def r_user(name_or_user):
    u = name_or_user if isinstance(name_or_user, User) else User.query.filter_by(name=name_or_user, active=True).first()
    return {"name": u.name, "email": u.email, "phone": u.phone} if u else None


def r_school(req: DemoRequest):
    s = req.school
    return {"name": f"{s.contact} ({s.name})", "email": s.email, "phone": s.mobile}


def r_dist(req: DemoRequest):
    d = req.distributor
    return {"name": d.org or d.name, "email": d.email, "phone": d.phone}


def r_team(role, label):
    users = User.query.filter_by(role=role, active=True).all()
    return {"name": label, "email": ", ".join(u.email for u in users), "phone": ""}


def notify(event, recipients, message, ref=None):
    recipients = [r for r in recipients if r]
    n = Notification(at=now(), event=event, message=message, ref=ref, recipients=recipients,
                     status="Queued" if current_app.config["SEND_MESSAGES"] else "Logged (sending off)")
    db.session.add(n)
    if current_app.config["SEND_MESSAGES"]:
        try:
            _send(event, recipients, message)
            n.status = "Sent"
        except Exception as e:  # never break the business action because a message failed
            n.status = f"Failed: {str(e)[:30]}"
    return n


def _send(event, recipients, message):
    cfg = current_app.config
    emails = [e.strip() for r in recipients for e in (r.get("email") or "").split(",") if e.strip()]
    if cfg["SMTP_HOST"] and emails:
        msg = EmailMessage()
        msg["Subject"] = f"Myjo Publications · {event}"
        msg["From"] = cfg["SMTP_FROM"]
        msg["Bcc"] = ", ".join(emails)
        msg.set_content(message)
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=10) as s:
            s.starttls()
            if cfg["SMTP_USER"]:
                s.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
            s.send_message(msg)
    if cfg["WHATSAPP_TOKEN"] and cfg["WHATSAPP_PHONE_ID"]:
        for r in recipients:
            if not r.get("phone"):
                continue
            body = json.dumps({"messaging_product": "whatsapp", "to": "91" + r["phone"][-10:], "type": "text",
                               "text": {"body": f"{event}\n{message}"}}).encode()
            q = urllib.request.Request(f"https://graph.facebook.com/v20.0/{cfg['WHATSAPP_PHONE_ID']}/messages", data=body,
                                       headers={"Authorization": f"Bearer {cfg['WHATSAPP_TOKEN']}", "Content-Type": "application/json"})
            urllib.request.urlopen(q, timeout=10).read()
