from flask import Blueprint
from .. import constants as C
from ..models import Series, Subject, User
from ..security import login_required

bp = Blueprint("meta", __name__)


@bp.get("/meta")
@login_required
def meta():
    people = {r: [u.name for u in User.query.filter_by(role=r, active=True).order_by(User.name)] for r in ("demo", "mkt", "acad")}
    series = Series.query.order_by(Series.id).all()
    return {
        "classes": C.CLASSES, "academic_years": C.ACADEMIC_YEARS, "boards": C.BOARDS,
        "subjects": [s.name for s in Subject.query.filter_by(active=True).order_by(Subject.id)],
        "series": [{"name": s.name, "color": s.color} for s in series if s.active],
        "all_series_colors": {s.name: s.color for s in series},
        "request_statuses": C.REQUEST_STATUSES, "order_statuses": C.ORDER_STATUSES, "confirmed_statuses": list(C.CONFIRMED),
        "training_statuses": C.TRAINING_STATUSES, "paper_statuses": C.PAPER_STATUSES, "resource_statuses": C.RESOURCE_STATUSES,
        "exam_types": C.EXAM_TYPES, "resource_types": C.RESOURCE_TYPES, "training_types": C.TRAINING_TYPES,
        "followup_methods": C.FOLLOWUP_METHODS, "payment_statuses": C.PAYMENT_STATUSES, "discussion_stages": C.DISCUSSION_STAGES,
        "requested_items": C.REQUESTED_ITEMS, "interest_levels": C.INTEREST, "access_levels": [C.ACCESS_ALL, C.ACCESS_SELECTED],
        "people": people,
        "distributors": [{"id": u.id, "name": u.org or u.name, "phone": u.phone}
                         for u in User.query.filter_by(role="dist", active=True).order_by(User.org)],
        "role_labels": C.ROLE_LABELS,
    }
