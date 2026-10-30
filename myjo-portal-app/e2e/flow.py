"""Browser flow: distributor places a final order (with PO upload) -> school portal opens -> academic team sees it."""
import json, re, urllib.request
from datetime import date, datetime, timedelta
from playwright.sync_api import sync_playwright, expect

import sys
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4173"
problems = []


def api(path, token=None, body=None):
    req = urllib.request.Request(BASE + "/api" + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})},
                                 method="POST" if body is not None else "GET")
    return json.loads(urllib.request.urlopen(req).read())


def sign_in(page, tile, user, pw):
    page.goto(BASE + "/")
    page.get_by_role("button", name=tile).first.click()
    page.fill("#lgname", user); page.fill("#lgpw", pw)
    page.locator("button[type=submit]").click()
    page.wait_for_function("() => !!sessionStorage.getItem('myjo-session')", timeout=15000)
    page.wait_for_timeout(300)
    if page.locator("#np1").count():
        page.fill("#np1", "School2026x"); page.fill("#np2", "School2026x"); page.fill("#pn1", "4826"); page.fill("#pn2", "4826")
        page.locator("button[type=submit]").click()
        page.wait_for_function("() => JSON.parse(sessionStorage.getItem('myjo-session')||'{}').must_change === false", timeout=15000)
    page.wait_for_load_state("networkidle")


import os
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/out") if os.path.isdir(os.path.dirname(os.path.abspath(__file__)) + "/out") else None
with open("po.pdf", "wb") as f:
    f.write(b"%PDF-1.4\n% PO copy\n")

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 1280, "height": 1000})
    page.on("pageerror", lambda e: problems.append(f"JS error: {e}"))
    page.on("response", lambda r: "/api/" in r.url and r.status >= 500 and problems.append(f"API {r.status} {r.url}"))

    # 1. Distributor: order for Holy Cross Academy
    sign_in(page, "Distributor", "royalstationery", "Smoke2026x")
    page.goto(BASE + "/my-orders"); page.wait_for_load_state("networkidle")
    page.get_by_role("row", name="Holy Cross Academy Bengaluru").get_by_role("button").click()
    dlg = page.locator("[role=dialog]")
    dlg.locator("button[type=submit]").click()                       # empty submit -> validation
    page.wait_for_timeout(300)
    if not dlg.locator(".ferr, [role=alert]").count():
        problems.append("empty order form showed no validation error")
    dlg.locator("select[name=order_status]").select_option("Order Confirmed")
    dlg.locator("select[name=ay]").select_option("2027-28")
    dlg.locator("input[name=po]").fill("HCA/BLR/PO/2027-01")
    dlg.get_by_label("Myjo English Reader").check()
    for c in ("1", "2"):
        dlg.get_by_label(c, exact=True).first.check()
    dlg.get_by_label("English", exact=True).check()
    dlg.get_by_label("Urdu", exact=True).check()
    dlg.locator("input[name=qty]").fill("12.5")
    dlg.locator("input[name=conf_date]").fill(date.today().isoformat())
    dlg.locator("input[name=del_date]").fill((date.today() + timedelta(days=20)).isoformat())
    dlg.locator("select[name=payment]").select_option("Pending")
    dlg.locator("input[name=files]").set_input_files("po.pdf")
    dlg.locator("input[name='pack.training_at']").fill((datetime.now() + timedelta(days=10)).strftime("%Y-%m-%dT10:00"))
    dlg.locator("select[name='pack.training_mode']").select_option("Offline")
    dlg.locator("input[name='pack.teachers']").fill("12")
    dlg.locator("textarea[name='pack.venue']").fill("School auditorium")
    dlg.get_by_label("Unit Test").check(); dlg.get_by_label("Annual").check()
    dlg.locator("input[name='pack.papers_by']").fill((date.today() + timedelta(days=25)).isoformat())
    dlg.locator("button[type=submit]").click(); page.wait_for_timeout(800)
    if "whole number" not in dlg.inner_text():
        problems.append("12.5 books was not refused with a whole-number message")
    dlg.locator("input[name=qty]").fill("480")
    dlg.locator("button[type=submit]").click()
    expect(dlg).to_have_count(0, timeout=15000)
    page.wait_for_load_state("networkidle")
    page.screenshot(path="flow-1-dist-after.png", full_page=True)

    # 2. Check through the API (admin) that it is final and set up
    tok = api("/auth/login", body={"role": "admin", "username": "syed.sufiyan", "pin": "4826"})["token"]
    rid = next(x["id"] for x in api("/requests", tok)["items"] if x["school"]["name"] == "Holy Cross Academy")
    det = api(f"/requests/{rid}", tok)
    print("status:", det["status"], "| order qty:", det["order"]["qty"], "| coverage:", det["academic"]["coverage"])
    print("papers:", len(det["academic"]["papers"]), "| trainings:", [(t["no"], t["status"]) for t in det["academic"]["trainings"]])
    if det["status"] != "Converted" or not det["academic"]["coverage"]["complete"]:
        problems.append("order not converted with full academic support")
    # The form pre-fills classes/subjects from the demo request, so compute the expected count from what was saved.
    o, ps = det["order"], det["academic"]["papers"]
    exams = {p["exam"] for p in ps}
    if len(ps) != len(o["classes"]) * len(o["subjects"]) * len(exams) or not {"Unit Test", "Annual"} <= exams:
        problems.append(f"paper count {len(ps)} != classes x subjects x exams")
    files = json.dumps(det)
    if "po.pdf" not in files:
        problems.append("PO copy not attached")
    login = det["academic"]["login"]["username"]
    print("school login:", login)

    # 3. School signs in with the temporary login, sets own password, sees its portal
    page.evaluate("sessionStorage.clear()")
    sign_in(page, "School User", login, "Myjo@123")
    page.goto(BASE + "/portal"); page.wait_for_load_state("networkidle")
    body = page.locator("main").inner_text()
    if "Holy Cross Academy" not in body or "HCA/BLR/PO/2027-01" not in body:
        problems.append("school overview missing school name or PO")
    page.screenshot(path="flow-2-school-portal.png", full_page=True)
    page.goto(BASE + "/portal/training"); page.wait_for_load_state("networkidle")
    if "School auditorium" not in page.locator("main").inner_text() and "Holy Cross" not in page.locator("main").inner_text():
        problems.append("school training page does not show the auto-created session")
    page.screenshot(path="flow-3-school-training.png", full_page=True)
    for path in ("/requests", "/audit", "/users"):
        page.goto(BASE + path); page.wait_for_load_state("networkidle")
        if re.search(r"Demo requests|Audit trail|Users & roles", page.locator("main").inner_text()[:200]) and "not" not in page.locator("main").inner_text()[:300].lower():
            problems.append(f"school user could open staff page {path}")

    # 4. Academic team sees the new ordered school
    page.evaluate("sessionStorage.clear()")
    sign_in(page, "Academic Support Team", "meera.nair", "Smoke2026x")
    page.goto(BASE + "/ordered-schools"); page.wait_for_load_state("networkidle")
    if "Holy Cross Academy" not in page.locator("main").inner_text():
        problems.append("Holy Cross not in ordered schools")
    page.screenshot(path="flow-4-acad-ordered.png", full_page=True)
    b.close()

print("\n".join(problems) or "FLOW OK")
