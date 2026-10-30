"""SQLAlchemy models. MySQL 8 is the target; JSON columns hold small lists (classes, subjects, series)."""
from datetime import datetime
from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint, Index)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .extensions import db

S = lambda n=255: String(n)  # noqa: E731


class CancelMixin:
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    cancel_by: Mapped[str | None] = mapped_column(S(120))
    cancel_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancel_approved_by: Mapped[str | None] = mapped_column(S(120))
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @property
    def cancel_pending(self):
        return bool(self.cancel_reason) and not self.cancelled


class Sequence(db.Model):
    __tablename__ = "sequences"
    name: Mapped[str] = mapped_column(S(40), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class User(db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(S(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(S(160), nullable=False)
    email: Mapped[str] = mapped_column(S(190), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(S(20), nullable=False)
    role: Mapped[str] = mapped_column(S(16), nullable=False, index=True)
    org: Mapped[str | None] = mapped_column(S(160))
    school_request_id: Mapped[int | None] = mapped_column(ForeignKey("demo_requests.id", use_alter=True, name="fk_user_request"))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pw_hash: Mapped[str] = mapped_column(S(255), nullable=False)
    pin_hash: Mapped[str | None] = mapped_column(S(255))
    must_change: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Permission(db.Model):
    __tablename__ = "role_permissions"
    role: Mapped[str] = mapped_column(S(16), primary_key=True)
    kind: Mapped[str] = mapped_column(S(8), primary_key=True)   # screen | action
    code: Mapped[str] = mapped_column(S(40), primary_key=True)


class Series(db.Model):
    __tablename__ = "book_series"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(S(120), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(S(9), default="#4D7C8A", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Subject(db.Model):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(S(80), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class School(db.Model):
    __tablename__ = "schools"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(S(200), nullable=False)
    address: Mapped[str] = mapped_column(S(300), nullable=False)
    city: Mapped[str] = mapped_column(S(80), nullable=False, index=True)
    state: Mapped[str] = mapped_column(S(80), nullable=False, index=True)
    pincode: Mapped[str] = mapped_column(S(6), nullable=False)
    board: Mapped[str] = mapped_column(S(20), nullable=False)
    strength: Mapped[int | None] = mapped_column(Integer)
    contact: Mapped[str] = mapped_column(S(120), nullable=False)
    designation: Mapped[str] = mapped_column(S(80), nullable=False)
    mobile: Mapped[str] = mapped_column(S(15), nullable=False)
    email: Mapped[str] = mapped_column(S(190), nullable=False)
    distributor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DemoRequest(CancelMixin, db.Model):
    __tablename__ = "demo_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    no: Mapped[str] = mapped_column(S(24), unique=True, nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    distributor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    ay: Mapped[str] = mapped_column(S(9), nullable=False)
    classes: Mapped[list] = mapped_column(JSON, nullable=False)
    subjects: Mapped[list] = mapped_column(JSON, nullable=False)
    series: Mapped[list] = mapped_column(JSON, nullable=False)
    exp_qty: Mapped[int | None] = mapped_column(Integer)
    pref_date: Mapped[datetime | None] = mapped_column(Date)
    pref_time: Mapped[str | None] = mapped_column(S(5))
    remarks: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(S(24), default="New", nullable=False, index=True)
    order_status: Mapped[str | None] = mapped_column(S(24))
    assigned_to: Mapped[str | None] = mapped_column(S(120))
    direct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    school = relationship("School", lazy="joined")
    distributor = relationship("User", foreign_keys=[distributor_id], lazy="joined")
    schedule = relationship("DemoSchedule", uselist=False, lazy="joined", cascade="all, delete-orphan")
    feedback = relationship("DemoFeedback", uselist=False, lazy="select", cascade="all, delete-orphan")
    marketing = relationship("MarketingFeedback", uselist=False, lazy="select", cascade="all, delete-orphan")
    order = relationship("Order", uselist=False, lazy="joined", cascade="all, delete-orphan")
    dist_order = relationship("DistOrder", uselist=False, lazy="joined", cascade="all, delete-orphan")
    pack = relationship("AcademicPack", uselist=False, lazy="select", cascade="all, delete-orphan")
    notes = relationship("ReviewNote", order_by="ReviewNote.at", lazy="select", cascade="all, delete-orphan")
    followups = relationship("FollowUp", order_by="[FollowUp.at.desc(), FollowUp.id.desc()]", lazy="select", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_req_school_ay", "school_id", "ay"),)


class ReviewNote(db.Model):
    __tablename__ = "review_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), nullable=False, index=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    by: Mapped[str] = mapped_column(S(120))
    type: Mapped[str] = mapped_column(S(60))
    text: Mapped[str] = mapped_column(Text)


class DemoSchedule(db.Model):
    __tablename__ = "demo_schedules"
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    mode: Mapped[str] = mapped_column(S(8), nullable=False)
    presenter: Mapped[str] = mapped_column(S(120), nullable=False)
    marketing: Mapped[str] = mapped_column(S(120), nullable=False)
    platform: Mapped[str | None] = mapped_column(S(30))
    link: Mapped[str | None] = mapped_column(S(500))
    venue: Mapped[str | None] = mapped_column(Text)
    agenda: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    shared_at: Mapped[datetime | None] = mapped_column(DateTime)
    reminded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DemoFeedback(db.Model):
    __tablename__ = "demo_feedback"
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), primary_key=True)
    by: Mapped[str] = mapped_column(S(120), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    attendees: Mapped[str] = mapped_column(Text, nullable=False)
    designations: Mapped[str | None] = mapped_column(Text)
    classes: Mapped[list] = mapped_column(JSON, default=list)
    subjects: Mapped[list] = mapped_column(JSON, default=list)
    series: Mapped[list] = mapped_column(JSON, default=list)
    interest: Mapped[str] = mapped_column(S(8), nullable=False)
    requirements: Mapped[str | None] = mapped_column(Text)
    requested: Mapped[list] = mapped_column(JSON, default=list)
    objections: Mapped[str | None] = mapped_column(Text)
    competitor: Mapped[str | None] = mapped_column(S(120))
    next_follow: Mapped[datetime | None] = mapped_column(Date)
    remarks: Mapped[str | None] = mapped_column(Text)


class MarketingFeedback(db.Model):
    __tablename__ = "marketing_feedback"
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), primary_key=True)
    potential: Mapped[str] = mapped_column(S(8), nullable=False)
    dm_name: Mapped[str] = mapped_column(S(120), nullable=False)
    dm_desig: Mapped[str | None] = mapped_column(S(80))
    dm_mobile: Mapped[str | None] = mapped_column(S(15))
    dm_email: Mapped[str | None] = mapped_column(S(190))
    competitor: Mapped[str | None] = mapped_column(S(120))
    exp_qty: Mapped[int | None] = mapped_column(Integer)
    decision_date: Mapped[datetime | None] = mapped_column(Date)
    stage: Mapped[str | None] = mapped_column(S(40))
    remarks: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(S(255))
    next_follow: Mapped[datetime | None] = mapped_column(Date, index=True)
    person: Mapped[str] = mapped_column(S(120), nullable=False)
    reminded_on: Mapped[datetime | None] = mapped_column(Date)


class FollowUp(db.Model):
    __tablename__ = "followups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), nullable=False, index=True)
    at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    method: Mapped[str] = mapped_column(S(20), nullable=False)
    person: Mapped[str] = mapped_column(S(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    next_action: Mapped[str | None] = mapped_column(S(255))
    next_date: Mapped[datetime | None] = mapped_column(Date)
    by: Mapped[str] = mapped_column(S(120), nullable=False)


class Order(db.Model):
    """The confirmed book order of a school (one per request)."""
    __tablename__ = "orders"
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), primary_key=True)
    ay: Mapped[str] = mapped_column(S(9), nullable=False)
    po: Mapped[str] = mapped_column(S(80), nullable=False, unique=True)
    series: Mapped[list] = mapped_column(JSON, nullable=False)
    classes: Mapped[list] = mapped_column(JSON, nullable=False)
    subjects: Mapped[list] = mapped_column(JSON, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    conf_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    del_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    payment: Mapped[str] = mapped_column(S(20), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(S(12), default="myjo", nullable=False)


class DistOrder(db.Model):
    """An order placed by a distributor (final when direct, or awaiting Marketing review)."""
    __tablename__ = "distributor_orders"
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), primary_key=True)
    status: Mapped[str] = mapped_column(S(12), nullable=False)  # Submitted | Returned | Rejected | Accepted
    direct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ay: Mapped[str] = mapped_column(S(9), nullable=False)
    po: Mapped[str] = mapped_column(S(80), nullable=False, index=True)
    series: Mapped[list] = mapped_column(JSON, nullable=False)
    classes: Mapped[list] = mapped_column(JSON, nullable=False)
    subjects: Mapped[list] = mapped_column(JSON, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    req_delivery: Mapped[datetime] = mapped_column(Date, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    by: Mapped[str] = mapped_column(S(120), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(S(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)


class AcademicPack(db.Model):
    __tablename__ = "academic_packs"
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    by: Mapped[str] = mapped_column(S(120))
    training_id: Mapped[int | None] = mapped_column(ForeignKey("trainings.id"))
    paper_ids: Mapped[list] = mapped_column(JSON, default=list)
    resource_ids: Mapped[list] = mapped_column(JSON, default=list)


class Training(CancelMixin, db.Model):
    __tablename__ = "trainings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    no: Mapped[str] = mapped_column(S(12), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(S(200), nullable=False)
    type: Mapped[str] = mapped_column(S(40), nullable=False)
    ay: Mapped[str] = mapped_column(S(9), nullable=False)
    series: Mapped[list] = mapped_column(JSON, nullable=False)
    classes: Mapped[list] = mapped_column(JSON, nullable=False)
    subjects: Mapped[list] = mapped_column(JSON, nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(S(8), nullable=False)
    trainer: Mapped[str] = mapped_column(S(120), nullable=False)
    link: Mapped[str | None] = mapped_column(S(500))
    venue: Mapped[str | None] = mapped_column(Text)
    agenda: Mapped[str] = mapped_column(Text, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(S(12), default="Draft", nullable=False, index=True)
    resource_ids: Mapped[list] = mapped_column(JSON, default=list)
    completion: Mapped[dict | None] = mapped_column(JSON)
    reminded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminded_on: Mapped[datetime | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    schools = relationship("TrainingSchool", cascade="all, delete-orphan", lazy="selectin", order_by="TrainingSchool.id")
    history = relationship("TrainingHistory", cascade="all, delete-orphan", lazy="select", order_by="TrainingHistory.at.desc()")


class TrainingSchool(db.Model):
    __tablename__ = "training_schools"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id"), nullable=False, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), nullable=False, index=True)
    expected: Mapped[int] = mapped_column(Integer, nullable=False)
    school_confirm: Mapped[str | None] = mapped_column(S(10))
    school_teachers: Mapped[int | None] = mapped_column(Integer)
    attended: Mapped[int | None] = mapped_column(Integer)
    attendance: Mapped[str | None] = mapped_column(S(20))
    myjo_feedback: Mapped[str | None] = mapped_column(Text)
    fb_rating: Mapped[int | None] = mapped_column(Integer)
    fb_text: Mapped[str | None] = mapped_column(Text)
    fb_attended: Mapped[int | None] = mapped_column(Integer)
    fb_by: Mapped[str | None] = mapped_column(S(120))
    fb_at: Mapped[datetime | None] = mapped_column(DateTime)
    request = relationship("DemoRequest", lazy="joined")
    __table_args__ = (UniqueConstraint("training_id", "request_id"),)


class TrainingHistory(db.Model):
    __tablename__ = "training_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id"), nullable=False, index=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    by: Mapped[str] = mapped_column(S(120))
    school: Mapped[str] = mapped_column(S(200))
    action: Mapped[str] = mapped_column(Text)


class File(db.Model):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(S(255), nullable=False)
    stored: Mapped[str] = mapped_column(S(80), nullable=False, unique=True)
    mime: Mapped[str] = mapped_column(S(120), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Attachment(db.Model):
    """Files attached to a record (demo feedback, distributor order, training completion)."""
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity: Mapped[str] = mapped_column(S(30), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    file = relationship("File", lazy="joined")
    __table_args__ = (Index("ix_attach_entity", "entity", "entity_id"),)


class QuestionPaper(CancelMixin, db.Model):
    __tablename__ = "question_papers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    no: Mapped[str] = mapped_column(S(12), unique=True, nullable=False)
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), nullable=False, index=True)
    ay: Mapped[str] = mapped_column(S(9), nullable=False)
    cls: Mapped[str] = mapped_column(S(10), nullable=False)
    subject: Mapped[str] = mapped_column(S(80), nullable=False)
    series: Mapped[str] = mapped_column(S(120), nullable=False)
    exam: Mapped[str] = mapped_column(S(20), nullable=False)
    due_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    assignee: Mapped[str | None] = mapped_column(S(120))
    max_marks: Mapped[int | None] = mapped_column(Integer)
    delivery_date: Mapped[datetime | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(S(20), default="New", nullable=False, index=True)
    qp_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    ak_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    remarks: Mapped[str | None] = mapped_column(Text)
    raised_by: Mapped[str] = mapped_column(S(30), default="Myjo")
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    reminded_on: Mapped[datetime | None] = mapped_column(Date)
    request = relationship("DemoRequest", lazy="joined")
    qp_file = relationship("File", foreign_keys=[qp_file_id], lazy="joined")
    ak_file = relationship("File", foreign_keys=[ak_file_id], lazy="joined")


class PaperRevocation(db.Model):
    __tablename__ = "paper_revocations"
    paper_id: Mapped[int] = mapped_column(ForeignKey("question_papers.id"), primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), primary_key=True)


class Resource(CancelMixin, db.Model):
    __tablename__ = "resources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    no: Mapped[str] = mapped_column(S(12), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(S(200), nullable=False)
    type: Mapped[str] = mapped_column(S(40), nullable=False)
    series: Mapped[str] = mapped_column(S(120), nullable=False, index=True)
    cls: Mapped[str] = mapped_column(S(12), nullable=False)
    subject: Mapped[str] = mapped_column(S(80), nullable=False)
    ay: Mapped[str] = mapped_column(S(9), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    link: Mapped[str | None] = mapped_column(S(500))
    version: Mapped[str] = mapped_column(S(20), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(S(120), nullable=False)
    access: Mapped[str] = mapped_column(S(30), nullable=False)
    status: Mapped[str] = mapped_column(S(12), default="Draft", nullable=False, index=True)
    file = relationship("File", lazy="joined")


class ResourceSchool(db.Model):
    __tablename__ = "resource_schools"
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), primary_key=True)


class ResourceRevocation(db.Model):
    __tablename__ = "resource_revocations"
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), primary_key=True)


class Download(db.Model):
    __tablename__ = "downloads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("demo_requests.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user_name: Mapped[str] = mapped_column(S(160), nullable=False)
    school_name: Mapped[str] = mapped_column(S(200), nullable=False)
    kind: Mapped[str] = mapped_column(S(20), nullable=False)    # Question paper | Answer key | Resource
    item_ref: Mapped[str] = mapped_column(S(20), nullable=False)
    item: Mapped[str] = mapped_column(S(300), nullable=False)
    file_name: Mapped[str] = mapped_column(S(255), nullable=False)


class Notification(db.Model):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    event: Mapped[str] = mapped_column(S(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    ref: Mapped[str | None] = mapped_column(S(40))
    recipients: Mapped[list] = mapped_column(JSON, nullable=False)
    channel: Mapped[str] = mapped_column(S(30), default="Email + WhatsApp")
    status: Mapped[str] = mapped_column(S(40), default="Queued")


class AuditLog(db.Model):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer)
    user_label: Mapped[str] = mapped_column(S(200), nullable=False)
    entity: Mapped[str] = mapped_column(S(40), nullable=False, index=True)
    ref: Mapped[str] = mapped_column(S(60), nullable=False, index=True)
    action: Mapped[str] = mapped_column(S(80), nullable=False)
    field: Mapped[str | None] = mapped_column(S(60))
    old: Mapped[str | None] = mapped_column(Text)
    new: Mapped[str | None] = mapped_column(Text)
