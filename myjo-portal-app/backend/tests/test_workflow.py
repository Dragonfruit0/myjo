"""End-to-end pipeline: request → review → schedule → feedback → marketing → order → academic pack."""
from conftest import SCHOOL, d, dt, order, pack, rid

BODY = {"school": SCHOOL, "ay": "2027-28", "classes": ["1", "2"], "subjects": ["English"], "series": ["Myjo English Reader"],
        "exp_qty": 200, "pref_date": d(5), "pref_time": "10:00"}


def err(r):
    return r.get_json().get("error", "")


def test_request_validation(as_):
    dist = as_("dist")
    assert "6 digits" in err(dist.post("/api/requests", {**BODY, "school": {**SCHOOL, "pincode": "4110"}}))
    assert "mobile" in err(dist.post("/api/requests", {**BODY, "school": {**SCHOOL, "mobile": "12345"}}))
    assert "email" in err(dist.post("/api/requests", {**BODY, "school": {**SCHOOL, "email": "bad@"}}))
    assert "past" in err(dist.post("/api/requests", {**BODY, "pref_date": d(-1)}))
    assert "required" in err(dist.post("/api/requests", {**BODY, "classes": []}))
    assert "whole number" in err(dist.post("/api/requests", {**BODY, "exp_qty": 12.5}))


def test_full_pipeline(as_):
    r = as_("dist").post("/api/requests", BODY)
    assert r.status_code == 201
    req = r.get_json()
    assert req["no"].startswith("MYJO-DR-") and req["status"] == "New"
    assert as_("dist").post("/api/requests", BODY).status_code == 409  # duplicate school + city + year
    i = req["id"]
    demo = as_("demo")
    assert demo.post(f"/api/requests/{i}/review").get_json()["status"] == "Under Review"
    assert "required" in err(demo.post(f"/api/requests/{i}/reject", {"reason": ""}))
    assert demo.post(f"/api/requests/{i}/approve").get_json()["status"] == "Approved"
    s = {"at": dt(3, 11), "mode": "Online", "presenter": "Priya Sharma", "marketing": "Neha Gupta", "platform": "Zoom", "link": "https://zoom.us/j/1"}
    assert "future" in err(demo.put(f"/api/requests/{i}/schedule", {**s, "at": dt(-1)}))
    assert "meeting link" in err(demo.put(f"/api/requests/{i}/schedule", {**s, "link": ""}))
    assert "https" in err(demo.put(f"/api/requests/{i}/schedule", {**s, "link": "javascript:alert(1)"}))
    assert "venue" in err(demo.put(f"/api/requests/{i}/schedule", {**s, "mode": "Offline"}))
    assert demo.put(f"/api/requests/{i}/schedule", s).get_json()["status"] == "Demo Scheduled"
    shared = demo.post(f"/api/requests/{i}/share").get_json()
    assert shared["schedule"]["shared_at"] and "Join link" in shared["message"]
    fb = {"by": "Priya Sharma", "date": d(0), "attendees": "Principal", "series": ["Myjo English Reader"], "interest": "High"}
    assert "future" in err(demo.put(f"/api/requests/{i}/feedback", {**fb, "date": d(2)}))
    assert demo.put(f"/api/requests/{i}/feedback", fb).get_json()["status"] == "Demo Completed"
    mkt = as_("mkt")
    assert mkt.put(f"/api/requests/{i}/marketing", {"potential": "High", "person": "Neha Gupta", "dm_name": "T P"}).get_json()["status"] == "Follow-up Pending"
    assert "after" in err(mkt.post(f"/api/requests/{i}/followups", {"at": dt(0), "method": "Call", "person": "T", "summary": "s", "next_date": d(-2)}))
    assert mkt.post(f"/api/requests/{i}/followups", {"at": dt(0), "method": "Call", "person": "T", "summary": "Price", "next_date": d(4)}).status_code == 201
    # order: validation
    assert "required" in err(mkt.put(f"/api/requests/{i}/order", {**order("QA/1"), "qty": None}))
    assert "before" in err(mkt.put(f"/api/requests/{i}/order", {**order("QA/1"), "del_date": d(-3)}))
    assert "already used" in err(mkt.put(f"/api/requests/{i}/order", {**order("DPSW/PO/2026/118"), "pack": pack()}))
    assert "training" in err(mkt.put(f"/api/requests/{i}/order", order("QA/1")))  # academic pack required
    q = mkt.put(f"/api/requests/{i}/order", {"order_status": "Quotation Sent"}).get_json()
    assert q["status"] == "Follow-up Pending"
    done = mkt.put(f"/api/requests/{i}/order", {**order("QA/1", series=["Myjo English Reader"], classes=["1", "2"], subjects=["English"]), "pack": pack()}).get_json()
    assert done["status"] == "Converted"
    ac = done["academic"]
    assert ac["coverage"]["training"] and ac["coverage"]["papers"] and ac["pack"] and ac["login"]["active"]
    assert len(ac["pack"]["paper_ids"]) == 4  # 2 classes x 1 subject x 2 exams
    assert "Only Admin" in err(mkt.put(f"/api/requests/{i}/order", {"order_status": "Not Interested"}))
    assert [s["done"] for s in done["steps"]] == [True] * 8


def test_admin_unconvert_closes_portal(as_):
    """Defect D2 from the prototype test report must stay fixed."""
    i = rid(as_, "QA Test School")
    r = as_("admin").put(f"/api/requests/{i}/order", {"order_status": "Not Interested"}).get_json()
    assert r["status"] == "Not Converted" and (r["academic"] is None or r["academic"]["eligible"] is False)
    ordered = [x["request_id"] for x in as_("acad").get("/api/ordered-schools").get_json()["items"]]
    assert i not in ordered


def test_hold_resume_reject(as_):
    i = rid(as_, "Holy Cross Academy")
    demo = as_("demo")
    assert demo.post(f"/api/requests/{i}/hold", {"reason": "Board meeting"}).get_json()["status"] == "On Hold"
    assert demo.post(f"/api/requests/{i}/resume").get_json()["status"] == "Under Review"
    assert demo.post(f"/api/requests/{i}/reject", {"reason": "Too small"}).get_json()["status"] == "Rejected"
    assert demo.post(f"/api/requests/{i}/approve").status_code == 409


def test_marketing_can_create_requests(as_):
    b = {**BODY, "school": {**SCHOOL, "name": "Mkt School"}, "distributor_id": as_("admin").get("/api/meta").get_json()["distributors"][0]["id"]}
    r = as_("mkt").post("/api/requests", b)
    assert r.status_code == 201 and r.get_json()["distributor"]["name"] == "Royal Stationery Book Depot"


def test_cancellation_needs_admin(as_):
    i = rid(as_, "Silver Oaks School")
    as_("demo").post(f"/api/requests/{i}/cancel", {"reason": "Duplicate"})
    assert as_("mgmt").get("/api/cancellations").status_code == 403
    pend = as_("admin").get("/api/cancellations").get_json()["items"]
    assert any(p["id"] == i for p in pend)
    as_("admin").post(f"/api/cancellations/request/{i}/approve")
    det = as_("admin").get(f"/api/requests/{i}").get_json()
    assert det["cancelled"] is True  # kept, not deleted
