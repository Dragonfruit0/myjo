"""Browser flow: menu badges, and a distributor WITHOUT 'confirm orders directly' adding a new school with an order
that Myjo Marketing then sees for review. Run after smoke.py (uses the passwords it set)."""
import json, sys, urllib.request
from datetime import date, timedelta
from playwright.sync_api import sync_playwright, expect

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4173"
problems = []


def api(path, token=None, body=None, method=None):
    req = urllib.request.Request(BASE + "/api" + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})},
                                 method=method or ("POST" if body is not None else "GET"))
    return json.loads(urllib.request.urlopen(req).read())


def sign_in(page, tile, user, pw="Smoke2026x"):
    page.evaluate("sessionStorage.clear()") if page.url.startswith("http") else None
    page.goto(BASE + "/")
    page.get_by_role("button", name=tile).first.click()
    page.fill("#lgname", user); page.fill("#lgpw", pw)
    page.locator("button[type=submit]").click()
    page.wait_for_function("() => !!sessionStorage.getItem('myjo-session')", timeout=15000)
    page.wait_for_load_state("networkidle")


admin = api("/auth/login", body={"role": "admin", "username": "syed.sufiyan", "pin": "4826"})["token"]
api("/permissions", admin, {"role": "dist", "kind": "action", "code": "directConfirm", "granted": False}, "PUT")
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 1000})
        page.on("pageerror", lambda e: problems.append(f"JS error: {e}"))
        page.on("response", lambda r: "/api/" in r.url and r.status >= 500 and problems.append(f"API {r.status} {r.url}"))

        # Menu badges for Marketing
        sign_in(page, "Marketing Team", "neha.gupta")
        page.goto(BASE + "/dashboard"); page.wait_for_load_state("networkidle")
        badge = page.locator("nav.side a.nav", has_text="Marketing & follow-ups").locator(".ct")
        if not badge.count():
            problems.append("no badge on 'Marketing & follow-ups' although a follow-up is overdue")
        before_orders = page.locator("nav.side a.nav", has_text="Book orders").locator(".ct")
        n_before = int(before_orders.inner_text()) if before_orders.count() else 0

        # Distributor in review mode adds a new school with its order
        sign_in(page, "Distributor", "royalstationery")
        page.goto(BASE + "/my-orders"); page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Create order").first.click()
        dlg = page.locator("[role=dialog]")
        dlg.locator("select[name=school]").select_option("__new")
        dlg.locator("button[type=submit]").click()
        page.wait_for_timeout(400)
        dlg = page.locator("[role=dialog]")
        if "Myjo Marketing" not in dlg.inner_text():
            problems.append("new-school form does not say Marketing will confirm")
        if dlg.locator("[name='pack.training_at']").count():
            problems.append("review-mode new-school form asks for training details")
        vals = {"school.name": "Green Meadows School", "school.address": "12 Lake Road", "school.city": "Mysuru",
                "school.state": "Karnataka", "school.pincode": "570002", "school.contact": "R. Iyer",
                "school.designation": "Principal", "school.mobile": "9845012345", "school.email": "office@greenmeadows.in",
                "po": "GMS/PO/27-1", "qty": "350", "del_date": (date.today() + timedelta(days=30)).isoformat()}
        for k, v in vals.items():
            el = dlg.locator(f"[name='{k}']")
            if el.evaluate("e => e.tagName") == "SELECT":
                el.select_option(v)
            else:
                el.fill(v)
        dlg.locator("select[name='school.board']").select_option(index=1)
        dlg.locator("select[name=ay]").select_option("2027-28")
        dlg.get_by_label("Myjo EVS Discovery").check()
        dlg.get_by_label("UKG", exact=True).check()
        dlg.get_by_label("EVS", exact=True).check()
        dlg.locator("button[type=submit]").click()
        expect(page.locator("[role=dialog]")).to_have_count(0, timeout=15000)
        page.wait_for_url("**/requests/*", timeout=15000)
        page.wait_for_load_state("networkidle")
        if not page.get_by_role("heading", name="Green Meadows School").count():
            problems.append("did not land on the new school's page")
        page.screenshot(path="out/review-1-dist-new-school.png", full_page=True)

        det = next(x for x in api("/requests", admin)["items"] if x["school"]["name"] == "Green Meadows School")
        det = api(f"/requests/{det['id']}", admin)
        print("status:", det["status"], "| dist order:", det["dist_order"]["status"], "| login:", det["academic"]["login"])
        if det["status"] == "Converted" or det["dist_order"]["status"] != "Submitted":
            problems.append("review-mode order should be Submitted, not converted")

        # Marketing sees it waiting, with a badge
        sign_in(page, "Marketing Team", "neha.gupta")
        page.goto(BASE + "/orders"); page.wait_for_load_state("networkidle")
        if "Green Meadows School" not in page.locator("main").inner_text():
            problems.append("Marketing does not see the order to review")
        after = page.locator("nav.side a.nav", has_text="Book orders").locator(".ct")
        if not after.count() or int(after.inner_text()) != n_before + 1:
            problems.append(f"'Book orders' badge did not go up by one (before {n_before})")
        page.screenshot(path="out/review-2-mkt-orders.png", full_page=True)
        b.close()
finally:
    api("/permissions/reset", admin, {})

print("\n".join(problems) or "REVIEW FLOW OK")
