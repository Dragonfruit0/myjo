"""Browser smoke test: every role signs in (first-time setup included) and opens every screen it is allowed.
Fails on JS errors, API 5xx, unexpected API 4xx, blank pages, or horizontal scroll at phone width.
usage: python smoke.py BASE_URL OUTDIR
"""
import json, sys, os
from playwright.sync_api import sync_playwright

BASE, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
ROLES = [("admin", "Admin", "syed.sufiyan"), ("mgmt", "Management", "nuzhat.khan"), ("demo", "Myjo Demo Team", "priya.sharma"),
         ("mkt", "Marketing Team", "neha.gupta"), ("acad", "Academic Support Team", "meera.nair"),
         ("dist", "Distributor", "royalstationery"), ("school", "School User", "dps.wagholi")]
PATH = {"dashboard": "/dashboard", "requests": "/requests", "marketing": "/marketing", "orders": "/orders", "myorders": "/my-orders",
        "acschools": "/ordered-schools", "training": "/training", "papers": "/papers", "resources": "/resources", "downloads": "/downloads",
        "reports": "/reports", "notifications": "/notifications", "audit": "/audit", "users": "/users", "masters": "/masters",
        "access": "/access", "portal": "/portal", "mytraining": "/portal/training", "library": "/portal/library",
        "support": "/portal/support", "history": "/portal/history"}
problems, visited = [], 0


def run(pw, role, tile, user, width):
    global visited
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": width, "height": 900})
    page = ctx.new_page()
    where = {"url": ""}
    page.on("pageerror", lambda e: problems.append(f"[{role}@{width}] JS error on {where['url']}: {e}"))
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and problems.append(f"[{role}@{width}] console: {m.text} on {where['url']}"))

    def on_resp(r):
        if "/api/" in r.url and r.status >= 400 and not r.url.endswith("/auth/login"):
            problems.append(f"[{role}@{width}] API {'(SCRIPT) ' if r.request.headers.get('x-smoke') else ''}{r.status} {r.request.method} {r.url.split('/api')[1]} on {where['url']}")
    page.on("response", on_resp)
    page.goto(BASE + "/")
    page.get_by_role("button", name=tile).first.click()
    page.fill("#lgname", user)
    page.fill("#lgpw", sys.argv[3] if len(sys.argv) > 3 else "Myjo@123")
    page.locator("button[type=submit]").click()
    page.wait_for_function("() => !!sessionStorage.getItem('myjo-session')", timeout=15000)
    page.wait_for_timeout(300)
    if page.locator("#np1").count():
        page.fill("#np1", "Smoke2026x"); page.fill("#np2", "Smoke2026x"); page.fill("#pn1", "4826"); page.fill("#pn2", "4826")
        page.locator("button[type=submit]").click()
        page.wait_for_function("() => (JSON.parse(sessionStorage.getItem('myjo-session') || '{}').must_change === false)", timeout=15000)
    tok = page.evaluate("() => (JSON.parse(sessionStorage.getItem('myjo-session') || '{}').token || '')")
    me = page.evaluate("async (t) => (await fetch('/api/auth/me', {headers: {Authorization: 'Bearer ' + t, 'X-Smoke': '1'}})).json()", tok)
    page.wait_for_load_state("networkidle")
    screens = me.get("screens", [])
    if not screens:
        problems.append(f"[{role}] no screens / not signed in: {json.dumps(me)[:200]}")
    extra = []
    if role in ("admin", "demo"):
        extra = ["/requests/1", "/requests/4"]
    if role == "acad":
        extra = ["/training/1", "/training/4"]
    if role == "dist":
        extra = ["/requests/7"]
    for path in [PATH[s] for s in screens if s in PATH] + extra:
        where["url"] = path
        page.goto(BASE + path)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(150)
        visited += 1
        txt = page.locator("main").inner_text() if page.locator("main").count() else page.inner_text("body")
        if len(txt.strip()) < 20:
            problems.append(f"[{role}@{width}] blank page {path}")
        for bad in ("undefined", "NaN", "[object Object]", "Something went wrong"):
            if bad in txt:
                problems.append(f"[{role}@{width}] '{bad}' shown on {path}")
        sw = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        if sw > 1:
            problems.append(f"[{role}@{width}] horizontal scroll {sw}px on {path}")
        if width < 500 or role in ("admin", "school", "dist"):
            page.screenshot(path=f"{OUT}/{role}-{width}-{path.strip('/').replace('/', '_') or 'home'}.png", full_page=False)
    b.close()


with sync_playwright() as pw:
    for role, tile, user in ROLES:
        run(pw, role, tile, user, 1280)
    # second pass at phone width; accounts now have their own password
    for role, tile, user in ROLES:
        sys.argv[3:] = ["Smoke2026x"]
        run(pw, role, tile, user, 390)

print(f"visited {visited} pages")
print("\n".join(sorted(set(problems))) or "NO PROBLEMS")
