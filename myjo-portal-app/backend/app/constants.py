"""Fixed lists and role definitions shared by the whole API."""

CLASSES = ["Nursery", "LKG", "UKG", "1", "2", "3", "4", "5"]
ACADEMIC_YEARS = ["2025-26", "2026-27", "2027-28"]
BOARDS = ["CBSE", "ICSE", "State Board", "Other"]

REQUEST_STATUSES = ["New", "Under Review", "Approved", "Rejected", "On Hold", "Demo Scheduled",
                    "Demo Completed", "Follow-up Pending", "Converted", "Not Converted"]
ORDER_STATUSES = ["Quotation Sent", "Sample Sent", "Under Discussion", "Order Confirmed",
                  "Partially Confirmed", "Not Interested", "Lost to Competitor", "On Hold"]
CONFIRMED = ("Order Confirmed", "Partially Confirmed")
LOST = ("Not Interested", "Lost to Competitor")
TRAINING_STATUSES = ["Draft", "Scheduled", "Completed", "Cancelled", "Closed"]
PAPER_STATUSES = ["New", "Assigned", "In Progress", "Ready for Review", "Published", "Delivered", "Closed"]
PAPER_LIVE = ("Published", "Delivered")
RESOURCE_STATUSES = ["Draft", "Published", "Archived"]
RESOURCE_TYPES = ["Teacher training manual", "Teaching guide", "Lesson plan", "PowerPoint presentation",
                  "Training video / link", "Worksheet", "Assessment guidelines", "Other academic resource"]
EXAM_TYPES = ["Unit Test", "Term Exam", "Half-Yearly", "Annual", "Other"]
TRAINING_TYPES = ["Product orientation", "Methodology workshop", "Digital resources",
                  "Assessment training", "Refresher session"]
FOLLOWUP_METHODS = ["Call", "Meeting", "WhatsApp", "Email", "School Visit"]
PAYMENT_STATUSES = ["Pending", "Advance Received", "Partially Paid", "Paid"]
DISCUSSION_STAGES = ["Initial discussion", "Samples under evaluation", "Quotation negotiation",
                     "Management approval", "Final decision"]
REQUESTED_ITEMS = ["Samples", "Brochures", "Quotation", "Presentation"]
INTEREST = ["High", "Medium", "Low"]
ACCESS_ALL = "All Ordered Schools"
ACCESS_SELECTED = "Selected Schools Only"

ROLES = ["admin", "mgmt", "demo", "mkt", "acad", "dist", "school"]
ROLE_LABELS = {"admin": "Admin", "mgmt": "Management", "demo": "Myjo Demo Team", "mkt": "Marketing Team",
               "acad": "Academic Support Team", "dist": "Distributor", "school": "School User"}

SCREENS = [("dashboard", "Dashboard"), ("requests", "Demo requests"), ("marketing", "Marketing & follow-ups"),
           ("orders", "Book orders"), ("myorders", "Distributor · My orders"), ("acschools", "Ordered schools"),
           ("training", "Teacher training"), ("papers", "Question papers"), ("resources", "Manuals & resources"),
           ("downloads", "Downloads"), ("reports", "Reports"), ("notifications", "Notifications"),
           ("audit", "Audit trail"), ("portal", "School · Overview"), ("mytraining", "School · Teacher training"),
           ("library", "School · Library & downloads"), ("support", "School · Support requests"),
           ("history", "School · Download history")]
ADMIN_ONLY_SCREENS = ["users", "masters", "access"]
INTERNAL_SCREENS = ["dashboard", "requests", "marketing", "orders", "acschools", "training", "papers",
                    "resources", "downloads", "reports", "notifications", "audit"]
SCHOOL_SCREENS = ["portal", "mytraining", "library", "support", "history"]
DIST_SCREENS = ["dashboard", "requests", "myorders"]

PERMS = [("createRequest", "Create demo requests"), ("editRequest", "Edit demo requests (before approval)"),
         ("placeOrder", "Place book orders for own schools (distributor)"),
         ("directConfirm", "Confirm own orders as final, no Myjo approval (distributor)"),
         ("review", "Review, approve, reject, hold & assign requests"), ("schedule", "Schedule demos & share links"),
         ("feedback", "Enter Myjo demo feedback"), ("marketing", "Marketing feedback & follow-ups"),
         ("order", "Update order status & convert schools"),
         ("academic", "Manage training, question papers & resources"),
         ("publish", "Publish & archive academic files"), ("revoke", "Revoke a school's access to files"),
         ("approveCancel", "Approve cancellations"), ("seeInternal", "See internal feedback & record audit trail")]

DEFAULT_SCREENS = {
    "admin": INTERNAL_SCREENS + ADMIN_ONLY_SCREENS,
    "mgmt": INTERNAL_SCREENS,
    "demo": ["dashboard", "requests", "reports", "notifications"],
    "mkt": ["dashboard", "requests", "marketing", "orders", "reports", "notifications"],
    "acad": ["dashboard", "orders", "acschools", "training", "papers", "resources", "downloads", "reports", "notifications"],
    "dist": ["dashboard", "requests", "myorders"],
    "school": SCHOOL_SCREENS,
}
DEFAULT_PERMS = {
    "createRequest": ["dist", "demo", "mkt"], "editRequest": ["dist", "demo", "mkt"],
    "placeOrder": ["dist"], "directConfirm": ["dist"],
    "review": ["demo"], "schedule": ["demo"], "feedback": ["demo"], "marketing": ["mkt"], "order": ["mkt"],
    "academic": ["acad"], "publish": ["acad"], "revoke": [], "approveCancel": [],
    "seeInternal": ["mgmt", "demo", "mkt", "acad"],
}


def screen_eligible(role, code):
    if role == "admin":
        return False
    if role == "school":
        return code in SCHOOL_SCREENS
    if role == "dist":
        return code in DIST_SCREENS
    return code in INTERNAL_SCREENS


def action_eligible(role, code):
    if role in ("admin", "school"):
        return False
    if role == "dist":
        return code in ("createRequest", "editRequest", "placeOrder", "directConfirm")
    return code not in ("placeOrder", "directConfirm")
