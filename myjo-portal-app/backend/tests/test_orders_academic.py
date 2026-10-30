from conftest import SCHOOL, d, dt, order, pack, rid


def err(r):
    return r.get_json().get("error", "")


def test_distributor_final_order_sets_up_academic_support(as_):
    i = rid(as_, "Navodaya Public School")
    dist = as_("dist")
    assert "future" in err(dist.post(f"/api/requests/{i}/dist-order", {**order("RS/1"), "pack": pack(training_at=dt(-1))}))
    assert "whole number" in err(dist.post(f"/api/requests/{i}/dist-order", {**order("RS/1", qty=12.5), "pack": pack()}))
    assert "whole number" in err(dist.post(f"/api/requests/{i}/dist-order", {**order("RS/1"), "pack": pack(teachers=2.5)}))
    r = dist.post(f"/api/requests/{i}/dist-order", {**order("RS/1"), "pack": pack()})
    assert r.status_code == 201, r.get_json()
    det = r.get_json()
    assert det["status"] == "Converted" and det["dist_order"]["direct"] is True
    assert det["academic"]["coverage"]["complete"] is True
    assert "dist_update" in det["actions"]


def test_distributor_updates_order(as_):
    i = rid(as_, "Navodaya Public School")
    r = as_("dist").put(f"/api/requests/{i}/dist-order", {**order("RS/1", payment="Paid")})
    assert r.status_code == 200 and r.get_json()["order"]["payment"] == "Paid"


def test_po_unique_across_all_order_paths(as_):
    """Defect D4: a pending distributor PO blocks the same PO elsewhere."""
    i = rid(as_, "Bharati Vidya Mandir")
    assert "already used" in err(as_("dist").post(f"/api/requests/{i}/dist-order", {**order("rs/1"), "pack": pack()}))


def test_online_without_link_is_draft_and_draft_does_not_count(as_):
    """Defect D3: draft training does not count toward coverage."""
    i = rid(as_, "Bharati Vidya Mandir")
    r = as_("dist").post(f"/api/requests/{i}/dist-order", {**order("RS/2"), "pack": pack(training_mode="Online")}).get_json()
    assert r["status"] == "Converted"
    assert r["academic"]["trainings"][0]["status"] == "Draft"
    assert r["academic"]["coverage"]["training"] is False


def test_new_school_one_step(as_):
    b = {"school": {**SCHOOL, "name": "QA Direct School", "city": "Hyderabad"}, "ay": "2027-28",
         "order": {**order("RS/NEW", subjects=["English", "Urdu"], series=["Myjo English Reader"], classes=["1"])}, "pack": pack(exams=["Unit Test"])}
    r = as_("dist").post("/api/direct-orders", b)
    assert r.status_code == 201, r.get_json()
    j = r.get_json()
    assert j["status"] == "Converted" and j["direct"] and len(j["academic"]["pack"]["paper_ids"]) == 2
    assert as_("dist").post("/api/direct-orders", {**b, "order": {**b["order"], "po": "RS/NEW2"}}).status_code == 409


def test_conversion_rate_never_exceeds_100(as_):
    """Defect D1: direct orders are reported separately from demo conversion."""
    k = {x["label"]: x["value"] for x in as_("mgmt").get("/api/dashboard").get_json()["kpis"]}
    assert int(str(k["Demo-to-order conversion"]).rstrip("%")) <= 100
    assert k["Direct distributor orders (no demo)"] >= 2
    rows = as_("mgmt").get("/api/reports/distributor").get_json()["rows"]
    assert all(float(r[-1].rstrip("%")) <= 100 for r in rows if r[-1] != "—")


def test_review_mode_and_rejection_deactivates_login(as_):
    """Defect D6: rejected distributor order deactivates the auto-created school login."""
    as_("admin").put("/api/permissions", {"role": "dist", "kind": "action", "code": "directConfirm", "granted": False})
    i = rid(as_, "Mount Carmel School")
    r = as_("dist").post(f"/api/requests/{i}/dist-order", order("RS/REV", series=["Myjo Computer Smart"], subjects=["Computer Science"])).get_json()
    assert r["dist_order"]["status"] == "Submitted" and r["status"] != "Converted"
    assert r["academic"]["eligible"] is True
    r = as_("mkt").post(f"/api/requests/{i}/dist-order/reject", {"reason": "Duplicate"}).get_json()
    assert r["dist_order"]["status"] == "Rejected"
    users = as_("admin").get("/api/users").get_json()["items"]
    assert not any(u["active"] for u in users if u["school_id"] == i)
    as_("admin").post("/api/permissions/reset")


def test_marketing_accepts_distributor_order(as_):
    as_("admin").put("/api/permissions", {"role": "dist", "kind": "action", "code": "directConfirm", "granted": False})
    i = rid(as_, "Saraswati Vidya Niketan")
    as_("dist").post(f"/api/requests/{i}/dist-order", order("RS/ACC", series=["Myjo Hindi Vatika"], subjects=["Hindi"], classes=["1"]))
    r = as_("mkt").post(f"/api/requests/{i}/dist-order/accept", {**order("RS/ACC", series=["Myjo Hindi Vatika"], subjects=["Hindi"], classes=["1"]), "pack": pack()})
    assert r.status_code == 200, r.get_json()
    j = r.get_json()
    assert j["status"] == "Converted" and j["dist_order"]["status"] == "Accepted" and j["academic"]["pack"]
    as_("admin").post("/api/permissions/reset")


def test_group_training_lifecycle(as_):
    acad = as_("acad")
    r1, r3 = rid(as_, "Delhi Public School, Wagholi"), rid(as_, "Sunrise International School, Kondapur")
    body = {"title": "QA Training", "type": "Methodology workshop", "ay": "2026-27", "series": ["Myjo Maths Pathways"], "classes": ["3"],
            "subjects": ["Mathematics"], "at": dt(5), "mode": "Online", "trainer": "Dr. Meera Nair", "link": "https://meet.google.com/x",
            "agenda": "A", "status": "Scheduled", "schools": [{"request_id": r1, "expected": 10}, {"request_id": r3, "expected": 8}]}
    assert "expected teachers" in err(acad.post("/api/trainings", {**body, "schools": [{"request_id": r1, "expected": 0}]}))
    assert "meeting link" in err(acad.post("/api/trainings", {**body, "link": ""}))
    t = acad.post("/api/trainings", body).get_json()
    assert t["status"] == "Scheduled" and len(t["schools"]) == 2
    mine = as_("school").get("/api/portal/trainings").get_json()["items"]
    assert any(x["id"] == t["id"] for x in mine)
    assert as_("school").post(f"/api/portal/trainings/{t['id']}/confirm", {"confirm": "Confirmed", "teachers": 9}).status_code == 200
    assert as_("school").post(f"/api/portal/trainings/{t['id']}/feedback", {"rating": 4, "attended": 9, "text": "x"}).status_code == 409
    assert "after the session" in err(acad.post(f"/api/trainings/{t['id']}/complete", {"status": "Completed", "trainer_remarks": "r", "schools": []}))


def test_training_completion_and_close(as_):
    acad = as_("acad")
    t = next(x for x in acad.get("/api/trainings").get_json()["items"] if x["title"] == "Assessment practices for primary classes")
    det = acad.get(f"/api/trainings/{t['id']}").get_json()
    rows = [{"request_id": s["request_id"], "attended": 5, "attendance": "Attended"} for s in det["schools"]]
    bad = [{**rows[0], "attendance": "Did not attend"}] + rows[1:]
    assert "Did not attend" in err(acad.post(f"/api/trainings/{t['id']}/complete", {"status": "Completed", "trainer_remarks": "r", "schools": bad}))
    ok = acad.post(f"/api/trainings/{t['id']}/complete", {"status": "Completed", "trainer_remarks": "Good", "schools": rows}).get_json()
    assert ok["status"] == "Completed"
    assert as_("school").post(f"/api/portal/trainings/{t['id']}/feedback", {"rating": 5, "attended": 5, "text": "Useful"}).status_code == 200
    assert acad.post(f"/api/trainings/{t['id']}/close").get_json()["status"] == "Closed"


def test_papers_and_resources(as_):
    acad = as_("acad")
    papers = acad.get("/api/papers").get_json()["items"]
    no_file = next(p for p in papers if p["status"] == "In Progress" and not p["qp_file"])
    assert acad.post(f"/api/papers/{no_file['id']}/publish").status_code == 400
    ready = next(p for p in papers if p["status"] == "Ready for Review")
    assert acad.post(f"/api/papers/{ready['id']}/publish").get_json()["status"] == "Published"
    res = {"title": "QA Res", "type": "Worksheet", "series": "Myjo EVS Discovery", "cls": "1", "subject": "EVS", "ay": "2026-27",
           "version": "1.0", "access": "All Ordered Schools", "status": "Draft"}
    assert "file or add a video link" in err(acad.post("/api/resources", res))
    assert "at least one school" in err(acad.post("/api/resources", {**res, "link": "https://v.myjo.in/x", "access": "Selected Schools Only"}))
    x = acad.post("/api/resources", {**res, "link": "https://v.myjo.in/x"}).get_json()
    acad.post(f"/api/resources/{x['id']}/publish")
    assert any(r["id"] == x["id"] for r in as_("school").get("/api/portal/library").get_json()["resources"])
    acad.post(f"/api/resources/{x['id']}/archive")
    assert not any(r["id"] == x["id"] for r in as_("school").get("/api/portal/library").get_json()["resources"])


def test_file_upload_and_school_download(as_, tmp_path):
    acad = as_("acad")
    up = acad.post("/api/files", data={"file": (__import__("io").BytesIO(b"%PDF-1.4 test"), "paper.pdf")}, content_type="multipart/form-data")
    assert up.status_code == 201
    fid = up.get_json()["id"]
    assert acad.post("/api/files", data={"file": (__import__("io").BytesIO(b"x"), "evil.exe")}, content_type="multipart/form-data").status_code == 400
    r1 = rid(as_, "Delhi Public School, Wagholi")
    p = acad.post("/api/papers", {"request_id": r1, "ay": "2026-27", "cls": "4", "subject": "Mathematics", "series": "Myjo Maths Pathways",
                                  "exam": "Annual", "due_date": d(10), "assignee": "Dr. Meera Nair", "status": "Published", "qp_file_id": fid}).get_json()
    r = as_("school").get(f"/api/files/{fid}/download?context=paper:{p['id']}:qp")
    assert r.status_code == 200 and r.data.startswith(b"%PDF")
    assert as_("school").post("/api/files", data={"file": (__import__("io").BytesIO(b"x"), "a.pdf")}, content_type="multipart/form-data").status_code == 403


def test_school_opens_video_link_and_it_is_recorded(as_):
    lib = as_("school").get("/api/portal/library").get_json()
    vid = next(x for x in lib["resources"] if x.get("link"))
    r = as_("school").post(f"/api/portal/resources/{vid['id']}/open")
    assert r.status_code == 200 and r.get_json()["link"] == vid["link"]
    hist = as_("school").get("/api/portal/history").get_json()["items"]
    assert hist[0]["file"] == vid["link"]


def test_new_school_order_for_review_when_not_direct(as_):
    """Distributors without 'confirm orders directly' can still add a new school with its order; Marketing then confirms."""
    as_("admin").put("/api/permissions", {"role": "dist", "kind": "action", "code": "directConfirm", "granted": False})
    b = {"school": {**SCHOOL, "name": "QA Review School", "city": "Mysuru", "state": "Karnataka", "pincode": "570001"}, "ay": "2027-28",
         "order": order("RS/REVNEW", series=["Myjo EVS Discovery"], subjects=["EVS"], classes=["1"])}
    r = as_("dist").post("/api/direct-orders", b)
    assert r.status_code == 201, r.get_json()
    j = r.get_json()
    assert j["status"] == "Follow-up Pending" and j["dist_order"]["status"] == "Submitted" and "Marketing" in j["message"]
    assert j["academic"]["eligible"] is True and j["academic"]["login"] is None   # login details are internal
    assert as_("admin").get(f"/api/requests/{j['id']}").get_json()["academic"]["login"]["active"] is True
    acc = as_("mkt").post(f"/api/requests/{j['id']}/dist-order/accept", {**b["order"], "pack": pack()})
    assert acc.status_code == 200 and acc.get_json()["status"] == "Converted"
    as_("admin").post("/api/permissions/reset")


def test_nav_counts(as_):
    c = as_("mkt").get("/api/nav-counts").get_json()["counts"]
    assert all(isinstance(v, int) and v > 0 for v in c.values())
    assert "marketing" in c  # seeded overdue follow-up
    assert "users" not in c and "audit" not in c
    assert as_("school").get("/api/nav-counts").get_json()["counts"] == {}
    d = as_("dist").get("/api/nav-counts").get_json()["counts"]
    assert "orders" not in d and "papers" not in d
