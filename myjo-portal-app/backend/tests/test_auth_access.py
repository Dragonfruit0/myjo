from app.models import User
from conftest import NEW_PIN, rid


def test_login_wrong_password_counts_attempts(api):
    r = api.c.post("/api/auth/login", json={"role": "mkt", "username": "arjun.rao", "password": "nope"})
    assert r.status_code == 401 and "4 attempt" in r.get_json()["error"]


def test_wrong_designation_refused(api):
    r = api.c.post("/api/auth/login", json={"role": "mkt", "username": "priya.sharma", "password": "Myjo@123"})
    assert r.status_code == 400 and "not a Marketing Team account" in r.get_json()["error"]


def test_unknown_user_generic_error(api):
    r = api.c.post("/api/auth/login", json={"role": "mkt", "username": "ghost", "password": "x"})
    assert r.status_code == 401 and "incorrect" in r.get_json()["error"]


def test_temporary_login_must_set_credentials(api):
    r = api.c.post("/api/auth/login", json={"role": "demo", "username": "karthik.iyer", "password": "Myjo@123"})
    body = r.get_json()
    assert body["must_change"] is True
    h = {"Authorization": f"Bearer {body['token']}"}
    assert api.c.get("/api/requests", headers=h).status_code == 403  # blocked until setup
    assert api.c.post("/api/auth/setup", json={"password": "short1", "pin": "4826"}, headers=h).status_code == 400
    assert "harder" in api.c.post("/api/auth/setup", json={"password": "Karthik2026", "pin": "1111"}, headers=h).get_json()["error"]
    r = api.c.post("/api/auth/setup", json={"password": "Karthik2026", "pin": "4826"}, headers=h)
    assert r.status_code == 200 and r.get_json()["must_change"] is False
    # old token invalidated (token version bumped)
    assert api.c.get("/api/meta", headers=h).status_code == 401


def test_pin_login_and_lockout(api, app):
    api.login("mkt", "neha.gupta")
    ok = api.c.post("/api/auth/login", json={"role": "mkt", "username": "neha.gupta", "pin": NEW_PIN})
    assert ok.status_code == 200
    for _ in range(4):
        api.c.post("/api/auth/login", json={"role": "mkt", "username": "neha.gupta", "pin": "0000"})
    r = api.c.post("/api/auth/login", json={"role": "mkt", "username": "neha.gupta", "pin": "0000"})
    assert r.status_code == 423
    r = api.c.post("/api/auth/login", json={"role": "mkt", "username": "neha.gupta", "pin": NEW_PIN})
    assert r.status_code == 423  # still locked with the right PIN


def test_admin_reset_unlocks(as_, api):
    users = as_("admin").get("/api/users").get_json()["items"]
    neha = next(u for u in users if u["username"] == "neha.gupta")
    assert neha["locked"] is True
    r = as_("admin").post(f"/api/users/{neha['id']}/reset", json={"temp_password": "Temp@1234", "temp_pin": "2468"})
    assert r.get_json()["locked"] is False and r.get_json()["temporary"] is True
    api.tokens.pop("neha.gupta", None)


def test_secrets_never_stored_plain(app):
    for u in User.query.all():
        assert u.pw_hash.startswith("pbkdf2:") and "Myjo@123" not in u.pw_hash


def test_screens_per_role(as_):
    assert "audit" not in as_("dist").get("/api/auth/me").get_json()["screens"]
    assert as_("dist").get("/api/audit").status_code == 403
    assert as_("school").get("/api/requests").status_code == 403
    assert as_("mgmt").get("/api/users").status_code == 403
    assert as_("demo").get("/api/reports").status_code == 200


def test_school_sees_only_own_published_material(as_):
    lib = as_("school").get("/api/portal/library").get_json()
    assert lib["papers"] and all(p["qp_file"] for p in lib["papers"])
    titles = [x["title"] for x in lib["resources"]]
    assert "Science Explorer Lab Activity Guide" not in titles          # draft
    assert "English Reader Lesson Plans, Class 4" not in titles         # another school's selected resource


def test_school_cannot_download_other_schools_paper(as_):
    papers = as_("admin").get("/api/papers").get_json()["items"]
    other = next(p for p in papers if p["school"].startswith("St. Xavier") and p["qp_file"])
    r = as_("school").get(f"/api/files/{other['qp_file']['id']}/download?context=paper:{other['id']}:qp")
    assert r.status_code == 403


def test_school_download_is_recorded(as_):
    lib = as_("school").get("/api/portal/library").get_json()
    p = lib["papers"][0]
    r = as_("school").get(f"/api/files/{p['qp_file']['id']}/download?context=paper:{p['id']}:qp")
    assert r.status_code == 200
    hist = as_("school").get("/api/portal/history").get_json()["items"]
    assert hist and hist[0]["file"] == p["qp_file"]["name"]


def test_revoked_paper_hidden(as_):
    lib = as_("school").get("/api/portal/library").get_json()
    p = lib["papers"][0]
    as_("admin").post(f"/api/papers/{p['id']}/revoke", json={"reason": "test"})
    lib2 = as_("school").get("/api/portal/library").get_json()
    assert p["id"] not in [x["id"] for x in lib2["papers"]]
    assert as_("school").get(f"/api/files/{p['qp_file']['id']}/download?context=paper:{p['id']}:qp").status_code == 403
    as_("admin").post(f"/api/papers/{p['id']}/restore")


def test_access_control_change_takes_effect(as_):
    as_("admin").put("/api/permissions", json={"role": "demo", "kind": "screen", "code": "reports", "granted": False})
    assert as_("demo").get("/api/reports").status_code == 403
    as_("admin").post("/api/permissions/reset")
    assert as_("demo").get("/api/reports").status_code == 200


def test_distributor_cannot_convert(as_):
    r4 = rid(as_, "Green Valley Public School")
    det = as_("dist").get(f"/api/requests/{r4}").get_json()
    assert "order" not in det["actions"] and det["feedback"] is None and det["marketing"] is None
    assert as_("dist").put(f"/api/requests/{r4}/order", json={"order_status": "Order Confirmed"}).status_code == 409
