from conftest import rid


def test_all_reports_and_filters(as_):
    m = as_("mgmt")
    keys = [r["key"] for r in m.get("/api/reports").get_json()["items"]]
    assert len(keys) == 17
    for k in keys:
        assert m.get(f"/api/reports/{k}").status_code == 200, k
        for f in ("state=Maharashtra", "series=Myjo%20Maths%20Pathways", "status=Converted", "cls=4", "from=2020-01-01&to=2030-01-01", "trainer=Dr.%20Meera%20Nair"):
            assert m.get(f"/api/reports/{k}?{f}").status_code == 200, (k, f)


def test_report_exports(as_):
    m = as_("mgmt")
    x = m.get("/api/reports/converted/export?format=xlsx")
    assert x.status_code == 200 and x.data[:2] == b"PK"
    p = m.get("/api/reports/converted/export?format=pdf")
    assert p.status_code == 200 and p.data[:4] == b"%PDF"
    c = m.get("/api/reports/requests/export?format=csv")
    assert c.status_code == 200 and b"Request no." in c.data


def test_totals(as_):
    j = as_("mgmt").get("/api/reports/converted").get_json()
    assert j["total"][0] == "Total" and j["total"][6] == sum(r[6] for r in j["rows"])


def test_masters(as_):
    a = as_("admin")
    assert "already exists" in a.post("/api/masters/subjects", {"name": "english"}).get_json()["error"]
    m = a.get("/api/masters").get_json()
    er = next(s for s in m["series"] if s["name"] == "Myjo English Reader")
    a.put(f"/api/masters/series/{er['id']}", {"name": "Myjo English Reader Plus"})
    det = a.get(f"/api/requests/{rid(as_, 'Holy Cross Academy')}").get_json()
    assert "Myjo English Reader Plus" in det["series"]
    eng = next(s for s in m["subjects"] if s["name"] == "English")
    assert a.delete(f"/api/masters/subjects/{eng['id']}").status_code == 409
    a.post("/api/masters/subjects", {"name": "Art"})
    art = next(s for s in a.get("/api/masters").get_json()["subjects"] if s["name"] == "Art")
    assert a.delete(f"/api/masters/subjects/{art['id']}").status_code == 200


def test_users_admin(as_):
    a = as_("admin")
    base = {"name": "X Y", "username": "neha.gupta", "email": "xy@myjo.in", "phone": "9820011099", "role": "demo", "temp_password": "Temp@1234", "temp_pin": "2468"}
    assert a.post("/api/users", base).status_code == 409
    r = a.post("/api/users", {**base, "username": "x.y"})
    assert r.status_code == 201
    me = next(u for u in a.get("/api/users").get_json()["items"] if u["username"] == "syed.sufiyan")
    assert a.post(f"/api/users/{me['id']}/toggle").status_code == 409


def test_audit_has_old_and_new(as_):
    items = as_("admin").get("/api/audit?q=English%20Reader").get_json()["items"]
    assert any(i["old"] == "Myjo English Reader" and i["new"].startswith("Myjo English Reader Plus") for i in items)


def test_reminders_once(as_):
    a = as_("admin")
    a.post("/api/reminders/run")
    assert a.post("/api/reminders/run").get_json()["sent"] == 0


def test_search(as_):
    s = as_("admin").get("/api/search?q=DPSW").get_json()
    assert any("Wagholi" in r["school"]["name"] for r in s["requests"])
    assert as_("dist").get("/api/search?q=Wagholi").get_json()["trainings"] == []


def test_xss_stored_as_text(as_):
    evil = '<img src=x onerror="alert(1)">'
    b = {"school": {"name": evil, "address": "R", "city": "Goa", "state": "Goa", "pincode": "403001", "board": "CBSE", "contact": "C",
                    "designation": "P", "mobile": "9876543210", "email": "a@b.in"},
         "ay": "2027-28", "classes": ["1"], "subjects": ["Hindi"], "series": ["Myjo Hindi Vatika"], "pref_date": "2099-01-01", "pref_time": "10:00"}
    r = as_("dist").post("/api/requests", b)
    assert r.status_code == 201 and r.get_json()["school"]["name"] == evil  # stored verbatim; the React UI renders it as text


def test_create_admin_cli_first_login(app, api):
    r = app.test_cli_runner().invoke(args=["create-admin", "--name", "Ops Admin", "--username", "ops.admin", "--email", "ops@myjo.in",
                                           "--phone", "9820000001", "--password", "Strong2026x"])
    assert r.exit_code == 0, r.output
    lg = api.c.post("/api/auth/login", json={"role": "admin", "username": "ops.admin", "password": "Strong2026x"}).get_json()
    assert lg["must_change"] is True
    h = {"Authorization": f"Bearer {lg['token']}"}
    assert api.c.post("/api/auth/setup", json={"password": "Stronger2026y", "pin": "4826"}, headers=h).status_code == 200
    weak = app.test_cli_runner().invoke(args=["create-admin", "--name", "W", "--username", "w", "--email", "w@m.in", "--phone", "9820000002", "--password", "short"])
    assert weak.exit_code != 0
