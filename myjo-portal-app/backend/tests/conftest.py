"""Test fixtures. Runs against MySQL when TEST_DATABASE_URL is set (recommended), otherwise in-memory SQLite.

    TEST_DATABASE_URL="mysql+pymysql://myjo:myjo@127.0.0.1:3306/myjo_test?charset=utf8mb4" pytest -q
"""
import tempfile
from datetime import date, datetime, timedelta
import pytest
from app import create_app
from app.config import TestConfig
from app.extensions import db

NEW_PW, NEW_PIN = "Test1234x", "4826"


class Cfg(TestConfig):
    UPLOAD_DIR = tempfile.mkdtemp(prefix="myjo-test-")


@pytest.fixture(scope="module")
def app():
    a = create_app(Cfg)
    with a.app_context():
        db.drop_all()
        db.create_all()
        from app.seed import seed_sample
        seed_sample()
        yield a
        db.session.remove()


class Api:
    """Thin client that signs in per username and remembers tokens."""

    def __init__(self, app):
        self.c = app.test_client()
        self.tokens = {}

    def login(self, role, username):
        if username in self.tokens:
            return self.tokens[username]
        r = self.c.post("/api/auth/login", json={"role": role, "username": username, "password": "Myjo@123"})
        assert r.status_code == 200, r.get_json()
        tok = r.get_json()["token"]
        if r.get_json()["must_change"]:
            r = self.c.post("/api/auth/setup", json={"password": NEW_PW, "pin": NEW_PIN}, headers={"Authorization": f"Bearer {tok}"})
            assert r.status_code == 200, r.get_json()
            tok = r.get_json()["token"]
        self.tokens[username] = tok
        return tok

    def as_(self, role, username):
        tok = self.login(role, username)
        api = self

        class Bound:
            def _h(self):
                return {"Authorization": f"Bearer {api.tokens.get(username, tok)}"}

            def get(self, url, **kw):
                return api.c.get(url, headers=self._h(), **kw)

            def post(self, url, json=None, **kw):
                if "data" in kw:
                    return api.c.post(url, headers=self._h(), **kw)
                return api.c.post(url, json=json if json is not None else {}, headers=self._h(), **kw)

            def put(self, url, json=None, **kw):
                return api.c.put(url, json=json or {}, headers=self._h(), **kw)

            def delete(self, url, **kw):
                return api.c.delete(url, headers=self._h(), **kw)
        return Bound()


@pytest.fixture(scope="module")
def api(app):
    return Api(app)


USERS = {"admin": ("admin", "syed.sufiyan"), "mgmt": ("mgmt", "nuzhat.khan"), "demo": ("demo", "priya.sharma"),
         "mkt": ("mkt", "neha.gupta"), "acad": ("acad", "meera.nair"), "dist": ("dist", "royalstationery"),
         "school": ("school", "dps.wagholi")}


@pytest.fixture(scope="module")
def as_(api):
    return lambda who: api.as_(*USERS[who])


def d(n):
    return (date.today() + timedelta(days=n)).isoformat()


def dt(n, h=10):
    return (datetime.now().replace(hour=h, minute=0, second=0, microsecond=0) + timedelta(days=n)).strftime("%Y-%m-%dT%H:%M")


def rid(as_, school_name):
    items = as_("admin").get("/api/requests").get_json()["items"]
    return next(x["id"] for x in items if x["school"]["name"] == school_name)


SCHOOL = {"name": "QA Test School", "address": "1 Test Road", "city": "Pune", "state": "Maharashtra", "pincode": "411001",
          "board": "CBSE", "strength": 500, "contact": "Test Person", "designation": "Principal", "mobile": "9876543210",
          "email": "qa@test.in"}
ORDER = {"order_status": "Order Confirmed", "ay": "2027-28", "series": ["Myjo Maths Pathways"], "classes": ["3", "4"],
         "subjects": ["Mathematics"], "qty": 300, "payment": "Pending"}


def order(po, **kw):
    return {**ORDER, "po": po, "conf_date": d(0), "del_date": d(15), **kw}


def pack(**kw):
    return {"training_at": dt(9), "training_mode": "Offline", "teachers": 10, "exams": ["Unit Test", "Term Exam"], "papers_by": d(20), **kw}
