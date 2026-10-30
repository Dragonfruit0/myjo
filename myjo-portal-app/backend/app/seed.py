"""Sample data matching the prototype (13 schools, one distributor). Dates are relative to today."""
from datetime import timedelta
from .extensions import db
from .models import (DemoFeedback, DemoRequest, DemoSchedule, FollowUp, MarketingFeedback, Order, QuestionPaper, Resource,
                     ResourceSchool, School, Sequence, Training, TrainingHistory, TrainingSchool, User, File, Notification)
from .security import hash_secret
from .util import now, today

PW, PIN = "Myjo@123", "2580"


def seed_sample():
    from .cli import seed_reference
    seed_reference()
    if User.query.first():
        raise SystemExit("Database already has users; seed only an empty database.")
    td, nw = today(), now()
    D = lambda n: td + timedelta(days=n)  # noqa: E731
    T = lambda n, h, m=0: (nw.replace(hour=h, minute=m) + timedelta(days=n))  # noqa: E731
    pw, pin = hash_secret(PW), hash_secret(PIN)

    def user(username, name, role, email, phone, org=None):
        u = User(username=username, name=name, role=role, email=email, phone=phone, org=org, pw_hash=pw, pin_hash=pin, must_change=True)
        db.session.add(u)
        return u
    user("syed.sufiyan", "Syed Sufiyan", "admin", "syed.sufiyan@myjo.in", "9820011001")
    user("nuzhat.khan", "Nuzhat Khan", "mgmt", "nuzhat.khan@myjo.in", "9820011002")
    user("priya.sharma", "Priya Sharma", "demo", "priya.sharma@myjo.in", "9820011003")
    user("karthik.iyer", "Karthik Iyer", "demo", "karthik.iyer@myjo.in", "9820011004")
    user("neha.gupta", "Neha Gupta", "mkt", "neha.gupta@myjo.in", "9820011005")
    user("arjun.rao", "Arjun Rao", "mkt", "arjun.rao@myjo.in", "9820011006")
    user("meera.nair", "Dr. Meera Nair", "acad", "meera.nair@myjo.in", "9820011007")
    user("sameer.joshi", "Sameer Joshi", "acad", "sameer.joshi@myjo.in", "9820011008")
    dist = user("royalstationery", "Royal Stationery Book Depot", "dist", "orders@royalstationerybooks.in", "9849244024", "Royal Stationery Book Depot")
    db.session.flush()
    seq = {}

    def no(name, prefix):
        seq[name] = seq.get(name, 0) + 1
        return f"{prefix}{str(seq[name]).zfill(4)}"

    def school_req(name, address, city, state, pin_, board, ay, contact, desig, mobile, email, classes, subjects, series, strength,
                   exp, pref, status, days_ago, **kw):
        s = School(name=name, address=address, city=city, state=state, pincode=pin_, board=board, strength=strength, contact=contact,
                   designation=desig, mobile=mobile, email=email, distributor_id=dist.id, created_at=T(-days_ago, 10))
        db.session.add(s)
        db.session.flush()
        r = DemoRequest(no=no("request", f"MYJO-DR-{td.year}-"), school_id=s.id, distributor_id=dist.id, ay=ay, classes=classes,
                        subjects=subjects, series=series, exp_qty=exp, pref_date=D(pref), pref_time="11:00", status=status,
                        created_at=T(-days_ago, 10), created_by=dist.id, **kw)
        db.session.add(r)
        db.session.flush()
        return r

    MP, ER, SE, EV, HV, CS = ("Myjo Maths Pathways", "Myjo English Reader", "Myjo Science Explorer", "Myjo EVS Discovery",
                              "Myjo Hindi Vatika", "Myjo Computer Smart")
    r1 = school_req("Delhi Public School, Wagholi", "Survey No. 42, Pune–Nagar Road", "Pune", "Maharashtra", "412207", "CBSE", "2026-27",
                    "Anita Deshpande", "Principal", "9881234501", "principal@dpswagholi.edu.in", ["3", "4", "5"], ["Mathematics", "Science"],
                    [MP, SE], 1450, 1200, -118, "Converted", 128, order_status="Order Confirmed", assigned_to="Priya Sharma")
    r2 = school_req("St. Xavier’s High School, Navrangpura", "Opp. Gujarat University, Navrangpura", "Ahmedabad", "Gujarat", "380009", "ICSE",
                    "2026-27", "Fr. Joseph D’Souza", "Principal", "9925011223", "principal@stxaviersnav.edu.in", ["1", "2", "3", "4", "5"],
                    ["English", "Computer Science"], [ER, CS], 1800, 900, -100, "Converted", 110, order_status="Order Confirmed", assigned_to="Karthik Iyer")
    r3 = school_req("Sunrise International School, Kondapur", "Plot 18, Botanical Garden Road, Kondapur", "Hyderabad", "Telangana", "500084",
                    "CBSE", "2026-27", "Kavitha Rao", "Academic Coordinator", "9989012345", "academics@sunriseintl.edu.in", ["1", "2", "3", "4", "5"],
                    ["EVS", "Hindi"], [EV, HV], 980, 700, -88, "Converted", 95, order_status="Partially Confirmed", assigned_to="Priya Sharma")
    r4 = school_req("Green Valley Public School", "Hingna Road, Near MIDC", "Nagpur", "Maharashtra", "440016", "State Board", "2027-28",
                    "Sunil Wankhede", "Director", "9823456710", "director@greenvalleynagpur.in", ["1", "2", "3", "4", "5"], ["Mathematics", "English"],
                    [MP, ER], 1250, 1000, -30, "Follow-up Pending", 40, order_status="Quotation Sent", assigned_to="Karthik Iyer")
    r5 = school_req("Little Flower Convent School", "Gunadala, Eluru Road", "Vijayawada", "Andhra Pradesh", "520004", "State Board", "2027-28",
                    "Sr. Mary Grace", "Headmistress", "9866123450", "office@littleflowervja.in", ["3", "4", "5"], ["Science", "EVS"], [SE, EV],
                    760, 450, 1, "Demo Scheduled", 12, assigned_to="Priya Sharma")
    school_req("Bharati Vidya Mandir", "Adajan Gam, Near Star Bazaar", "Surat", "Gujarat", "395009", "CBSE", "2027-28", "Hetal Shah",
                    "Vice Principal", "9825567812", "vp@bvmsurat.org", ["1", "2", "3", "4", "5"], ["Mathematics", "Science"], [MP, SE], 2100, 1500,
                    8, "Approved", 6, assigned_to="Karthik Iyer")
    school_req("Holy Cross Academy", "7th Cross, HRBR Layout", "Bengaluru", "Karnataka", "560043", "ICSE", "2027-28", "Deepa Menon", "Principal",
               "9845098765", "principal@holycrossblr.in", ["1", "2", "3", "4", "5"], ["English", "Computer Science"], [ER, CS], 900, 600, 9, "New", 1,
               remarks="Prefers Saturday morning.")
    school_req("Saraswati Vidya Niketan", "Scheme No. 54, Vijay Nagar", "Indore", "Madhya Pradesh", "452010", "CBSE", "2027-28", "Rakesh Tiwari",
               "Principal", "9826012345", "svn.indore@gmail.com", ["1", "2", "3", "4", "5"], ["Hindi", "EVS"], [HV, EV], 640, 400, 6, "Under Review", 3,
               assigned_to="Priya Sharma")
    r9 = school_req("Oakridge Model School", "Hanamkonda Main Road", "Warangal", "Telangana", "506001", "State Board", "2027-28", "V. Lakshmi",
                    "Correspondent", "9848022110", "oakridgewgl@gmail.com", ["3", "4", "5"], ["Science"], [SE], 820, 500, -62, "Not Converted", 70,
                    order_status="Lost to Competitor", assigned_to="Karthik Iyer")
    r10 = school_req("Navodaya Public School", "Gangapur Road", "Nashik", "Maharashtra", "422013", "CBSE", "2027-28", "Pradeep Kulkarni", "Principal",
                     "9890045123", "principal@navodayanashik.in", ["3", "4", "5"], ["Mathematics"], [MP], 1100, 650, -1, "Demo Scheduled", 15,
                     assigned_to="Karthik Iyer")
    school_req("Silver Oaks School", "Gotri Road", "Vadodara", "Gujarat", "390021", "CBSE", "2027-28", "Meenal Joshi", "Coordinator", "9824190876",
               "coordinator@silveroaksvadodara.in", ["3", "4", "5"], ["English"], [ER], 540, 300, -10, "On Hold", 22, assigned_to="Priya Sharma")
    school_req("Rainbow English School", "Brodipet 4th Line", "Guntur", "Andhra Pradesh", "522002", "State Board", "2027-28", "K. Ravi", "Manager",
               "9866554433", "rainbowgnt@gmail.com", ["1", "2"], ["English"], [ER], 180, 80, -44, "Rejected", 50)
    r13 = school_req("Mount Carmel School", "Vijayanagar 2nd Stage", "Mysuru", "Karnataka", "570017", "ICSE", "2027-28", "Sr. Lucy Thomas",
                     "Principal", "9845321098", "principal@mountcarmelmys.in", ["3", "4", "5"], ["Computer Science", "Mathematics"], [CS, MP],
                     1300, 800, -25, "Follow-up Pending", 34, order_status="Sample Sent", assigned_to="Priya Sharma")

    def sched(r, d, h, mode, presenter, mkt, link=None, platform=None, venue=None, agenda=""):
        r.schedule = DemoSchedule(request_id=r.id, at=T(d, h), mode=mode, presenter=presenter, marketing=mkt, platform=platform, link=link,
                                  venue=venue, agenda=agenda, shared_at=T(d - 1, 9) if d < 0 else None, reminded=d < 0)

    def fb(r, d, by, interest, competitor, series, att="Principal and HoDs"):
        r.feedback = DemoFeedback(request_id=r.id, by=by, date=D(d), attendees=att, designations="Principal, HoD", classes=r.classes,
                                  subjects=r.subjects, series=series, interest=interest, competitor=competitor, requested=["Samples"],
                                  next_follow=D(d + 5), requirements="Activity-based material")

    def mk(r, person, potential, stage, next_follow, next_action, exp):
        r.marketing = MarketingFeedback(request_id=r.id, person=person, potential=potential, dm_name=r.school.contact, dm_desig=r.school.designation,
                                        dm_mobile=r.school.mobile, dm_email=r.school.email, stage=stage, next_follow=next_follow,
                                        next_action=next_action, exp_qty=exp)

    def order(r, po, qty, d, payment, series=None):
        r.order = Order(request_id=r.id, ay=r.ay, po=po, series=series or r.series, classes=r.classes, subjects=r.subjects, qty=qty,
                        conf_date=D(d), del_date=D(d + 9), payment=payment, source="myjo")
    sched(r1, -115, 11, "Online", "Priya Sharma", "Neha Gupta", "https://meet.google.com/xke-pqra-wtn", "Google Meet", agenda="Maths Pathways 3–5")
    fb(r1, -115, "Priya Sharma", "High", "Oxford University Press", [MP, SE])
    mk(r1, "Neha Gupta", "High", "Final decision", D(-102), "Collect PO", 1200)
    order(r1, "DPSW/PO/2026/118", 1220, -104, "Paid")
    sched(r2, -98, 10, "Offline", "Karthik Iyer", "Arjun Rao", venue="Conference Hall, Admin Block", agenda="English Reader literature strand")
    fb(r2, -98, "Karthik Iyer", "High", "Frank Brothers", [ER, CS])
    mk(r2, "Arjun Rao", "High", "Final decision", D(-80), "Dispatch", 900)
    order(r2, "SXHS/2026/PO-77", 860, -80, "Partially Paid")
    sched(r3, -86, 14, "Online", "Priya Sharma", "Arjun Rao", "https://zoom.us/j/84512093321", "Zoom", agenda="EVS Discovery 1–5")
    fb(r3, -86, "Priya Sharma", "Medium", "Madhubun", [EV, HV])
    mk(r3, "Arjun Rao", "Medium", "Final decision", D(40), "Push Hindi 4–5 for next AY", 700)
    order(r3, "SIS/HYD/PO/2026-31", 640, -72, "Advance Received")
    sched(r4, -28, 11, "Online", "Karthik Iyer", "Neha Gupta", "https://zoom.us/j/81234567890", "Zoom", agenda="Maths Pathways 1–5")
    fb(r4, -28, "Karthik Iyer", "Medium", "Navneet", [MP, ER])
    mk(r4, "Neha Gupta", "Medium", "Quotation negotiation", D(-2), "Revised quotation call", 1000)
    sched(r5, 1, 11, "Online", "Priya Sharma", "Arjun Rao", "https://teams.microsoft.com/l/meetup-join/LFCS", "Microsoft Teams", agenda="EVS and Science bridge")
    sched(r9, -60, 10, "Offline", "Karthik Iyer", "Arjun Rao", venue="School auditorium", agenda="Science Explorer 3–5")
    fb(r9, -60, "Karthik Iyer", "Low", "S. Chand", [SE])
    mk(r9, "Arjun Rao", "Low", "Final decision", None, "Revisit next AY", 500)
    sched(r10, -1, 10, "Offline", "Karthik Iyer", "Neha Gupta", venue="Smart classroom, 2nd floor", agenda="Maths Pathways 3–5 with lab kit")
    sched(r13, -24, 10, "Online", "Priya Sharma", "Arjun Rao", "https://meet.google.com/mcs-yqzt-pkr", "Google Meet", agenda="Computer Smart 3–5")
    fb(r13, -24, "Priya Sharma", "High", "Kips", [CS, MP])
    mk(r13, "Arjun Rao", "High", "Samples under evaluation", D(3), "Collect sample feedback", 800)
    for r, d, m, person, summary, by in [(r1, -112, "Call", "Anita Deshpande", "Shared sample request", "Neha Gupta"),
                                          (r1, -106, "Meeting", "Anita Deshpande, HoDs", "Samples reviewed; quotation discussed", "Neha Gupta"),
                                          (r4, -20, "Call", "Sunil Wankhede", "Quotation shared; asked for 12% discount", "Neha Gupta"),
                                          (r4, -9, "WhatsApp", "A. Thakre", "Director travelling; asked to reconnect", "Neha Gupta"),
                                          (r9, -48, "Call", "V. Lakshmi", "School finalised another publisher", "Arjun Rao"),
                                          (r13, -10, "School Visit", "J. Pinto", "Delivered sample sets for 3–5", "Arjun Rao")]:
        db.session.add(FollowUp(request_id=r.id, at=T(d, 11), method=m, person=person, summary=summary, next_action="Follow up", next_date=D(d + 6), by=by))
    db.session.flush()
    # school logins for converted schools
    for r, username in [(r1, "dps.wagholi"), (r2, "stxaviers.navrangpura"), (r3, "sunrise.kondapur")]:
        db.session.add(User(username=username, name=r.school.contact, role="school", email=r.school.email, phone=r.school.mobile,
                            school_request_id=r.id, pw_hash=pw, pin_hash=pin, must_change=True))
    # sample files (names only; real files are uploaded through the portal)
    import os
    from flask import current_app
    def sample_file(name, size=120000):
        stored = f"sample-{name}"
        path = os.path.join(current_app.config["UPLOAD_DIR"], stored)
        if not os.path.exists(path):
            with open(path, "wb") as fh:
                fh.write(b"%PDF-1.4\n% Myjo sample file: " + name.encode() + b"\n%%EOF\n")
        f = File(name=name, stored=stored, mime="application/pdf", size=os.path.getsize(path), at=nw)
        db.session.add(f)
        db.session.flush()
        return f.id
    # resources
    def resource(title, type_, series, cls, subject, version, d, by, access, status, schools=(), link=None, file=None):
        x = Resource(no=no("resource", "RES-"), title=title, type=type_, series=series, cls=cls, subject=subject, ay="2026-27",
                     description=title, version=version, upload_date=D(d), uploaded_by=by, access=access, status=status,
                     link=link, file_id=sample_file(file) if file else None)
        db.session.add(x)
        db.session.flush()
        for rid in schools:
            db.session.add(ResourceSchool(resource_id=x.id, request_id=rid))
        return x
    m1 = resource("Maths Pathways Teacher Manual, Classes 3–5", "Teacher training manual", MP, "All classes", "Mathematics", "2.0", -60, "Dr. Meera Nair",
                  "All Ordered Schools", "Published", file="MP_TeacherManual_3-5_v2.pdf")
    resource("English Reader Lesson Plans, Class 4", "Lesson plan", ER, "4", "English", "1.1", -45, "Sameer Joshi", "Selected Schools Only", "Published",
             [r2.id], file="ER_C4_LessonPlans.pdf")
    resource("Science Explorer Lab Activity Guide", "Teaching guide", SE, "All classes", "Science", "0.9", -5, "Sameer Joshi", "All Ordered Schools", "Draft",
             file="SE_LabGuide_draft.pdf")
    m4 = resource("EVS Discovery Classroom Videos, Term 1", "Training video / link", EV, "All classes", "EVS", "1.0", -30, "Dr. Meera Nair",
                  "All Ordered Schools", "Published", link="https://videos.myjo.in/evs-discovery/term-1")
    resource("Hindi Vatika Worksheets, Classes 1–3", "Worksheet", HV, "All classes", "Hindi", "1.0", -20, "Sameer Joshi", "Selected Schools Only",
             "Published", [r3.id], file="HV_Worksheets_1-3.pdf")
    # question papers
    def paper(r, cls, subject, series, exam, due, assignee, status, qp=None, ak=None, marks=25, raised="Myjo"):
        p = QuestionPaper(no=no("paper", "QP-"), request_id=r.id, ay="2026-27", cls=cls, subject=subject, series=series, exam=exam, due_date=D(due),
                          assignee=assignee, status=status, max_marks=marks, raised_by=raised,
                          qp_file_id=sample_file(qp) if qp else None, ak_file_id=sample_file(ak) if ak else None,
                          published_at=T(due - 2, 10) if status in ("Published", "Delivered") else None)
        db.session.add(p)
        return p
    paper(r1, "5", "Mathematics", MP, "Half-Yearly", -20, "Dr. Meera Nair", "Published", "DPSW_C5_Maths_HY_QP.pdf", "DPSW_C5_Maths_HY_AK.pdf", 80)
    paper(r1, "3", "Science", SE, "Unit Test", 3, "Sameer Joshi", "In Progress", raised="School")
    paper(r2, "4", "English", ER, "Term Exam", -10, "Sameer Joshi", "Published", "SXHS_C4_English_Term1_QP.pdf", "SXHS_C4_English_Term1_AK.pdf", 80)
    paper(r3, "4", "EVS", EV, "Unit Test", -1, "Dr. Meera Nair", "Ready for Review", "SIS_C4_EVS_UT2_QP.pdf", "SIS_C4_EVS_UT2_AK.pdf", 20, "School")
    paper(r2, "5", "Computer Science", CS, "Unit Test", 12, None, "New", raised="School")
    # trainings
    def training(title, type_, series, classes, subjects, d, h, mode, trainer, status, schools, link=None, venue=None, completion=None):
        t = Training(no=no("training", "TR-"), title=title, type=type_, ay="2026-27", series=series, classes=classes, subjects=subjects,
                     at=T(d, h), mode=mode, trainer=trainer, link=link, venue=venue, agenda="Agenda: " + title, status=status,
                     resource_ids=[m1.id, m4.id], completion=completion, reminded=d < 0)
        for rid, exp, conf, att in schools:
            t.schools.append(TrainingSchool(request_id=rid, expected=exp, school_confirm=conf, school_teachers=exp if conf else None,
                                            attended=att, attendance="Attended" if att else None))
        db.session.add(t)
        db.session.flush()
        db.session.add(TrainingHistory(training_id=t.id, at=T(d - 5, 10), by=trainer, school="All schools", action=f"Session created as {status}"))
        return t
    training("Maths Pathways methodology workshop", "Methodology workshop", [MP], ["3", "4", "5"], ["Mathematics"], -88, 15, "Online", "Dr. Meera Nair",
             "Closed", [(r1.id, 14, "Confirmed", 14)], link="https://meet.google.com/mjt-wksp-001",
             completion={"status": "Completed", "trainer_remarks": "All lab-kit activities covered.", "follow_up": "Share fractions slides",
                         "recording": "", "at": (T(-88, 18)).strftime("%Y-%m-%dT%H:%M"), "by": "Dr. Meera Nair"})
    training("Term 2 orientation: Maths Pathways & EVS Discovery", "Product orientation", [MP, EV], ["1", "2", "3", "4", "5"], ["Mathematics", "EVS"],
             6, 15, "Online", "Sameer Joshi", "Scheduled", [(r1.id, 12, "Confirmed", None), (r3.id, 9, None, None)], link="https://zoom.us/j/86012345678")
    training("English Reader literature strand workshop", "Methodology workshop", [ER], ["1", "2", "3", "4", "5"], ["English"], 14, 10, "Offline",
             "Sameer Joshi", "Draft", [(r2.id, 22, None, None)], venue="Conference Hall, St. Xavier’s High School")
    training("Assessment practices for primary classes", "Assessment training", [SE, EV], ["3", "4", "5"], ["Science", "EVS"], -2, 11, "Online",
             "Dr. Meera Nair", "Scheduled", [(r1.id, 11, "Confirmed", None), (r3.id, 8, "Confirmed", None)], link="https://meet.google.com/mjt-asmt-004")
    db.session.add(Notification(at=nw, event="Sample data loaded", message="Portal sample data created", recipients=[], status="Logged"))
    for name, val in seq.items():
        s = db.session.get(Sequence, name) or Sequence(name=name, value=0)
        s.value = val
        db.session.add(s)
    db.session.commit()
