# Myjo Portal API (v1)

Base URL: `/api`. JSON in and out (`Content-Type: application/json`) except file upload (multipart) and report export (file download).
Field names are `snake_case`. Dates are `YYYY-MM-DD`; date-times are `YYYY-MM-DDTHH:MM` (server local time, Asia/Kolkata by default).

## Conventions

* **Auth**: `Authorization: Bearer <token>` on every call except `POST /auth/login`. Token lifetime 8 h.
* **Errors**: HTTP 4xx with `{"error": "Human readable message", "field": "optional_field_name"}`.
  400 validation, 401 not signed in / bad token, 403 not allowed, 404 not found, 409 conflict (duplicate, wrong state), 423 account locked.
* **Lists** return `{"items": [...], "total": n}`. Optional `?q=` search, `?status=` filter where noted.
* **Record actions**: every detail object includes `"actions": [..]` — the list of action codes the signed-in user may perform on that record *right now*. The front end shows a button only when its code is present.
* **Roles** (`role`): `admin`, `mgmt`, `demo`, `mkt`, `acad`, `dist`, `school`.
  Role labels: Admin, Management, Myjo Demo Team, Marketing Team, Academic Support Team, Distributor, School User.

---

## Auth

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| POST | `/auth/login` | `{"role":"mkt","username":"neha.gupta","password":"…"}` **or** `{"role":"mkt","username":"neha.gupta","pin":"4826"}` | `{"token","user","must_change": bool}` |
| POST | `/auth/setup` | `{"password","pin"}` (only when `must_change`) | `{"token","user","must_change":false}` |
| GET | `/auth/me` | – | `{"user","screens":[..],"perms":[..]}` |
| POST | `/auth/change` | `{"current_password","new_password"?,"new_pin"?}` | `{"ok":true}` |
| POST | `/auth/logout` | – | `{"ok":true}` (audited) |

`user` = `{"id","username","name","email","phone","role","role_label","org","school_id","school_name"}`.

Rules: password ≥ 8 chars with letters and digits; PIN exactly 4 digits, not trivial (1111, 1234, 4321, 0123, 9876).
5 wrong attempts → locked 5 min (HTTP 423). Wrong designation → 400 `"This account is not a <Role> account."`.
When `must_change` is true the token only allows `/auth/setup`, `/auth/me`, `/auth/logout`.

**Screens** (codes used in `screens` and menus):
`dashboard, requests, marketing, orders, myorders, acschools, training, papers, resources, downloads, reports, notifications, audit, users, masters, access, portal, mytraining, library, support, history`.

**Perms** (action permission codes): `createRequest, editRequest, placeOrder, directConfirm, review, schedule, feedback, marketing, order, academic, publish, revoke, approveCancel, seeInternal`.

## Meta

`GET /meta` →
```json
{
 "classes": ["Nursery","LKG","UKG","1","2","3","4","5"],
 "subjects": ["English", "..."],            // active only
 "series": [{"name":"Myjo Maths Pathways","color":"#1A73C9"}],  // active only
 "all_series_colors": {"Myjo Maths Pathways":"#1A73C9"},
 "academic_years": ["2025-26","2026-27","2027-28"],
 "boards": ["CBSE","ICSE","State Board","Other"],
 "request_statuses": [...], "order_statuses": [...], "training_statuses": [...], "paper_statuses": [...], "resource_statuses": [...],
 "exam_types": ["Unit Test","Term Exam","Half-Yearly","Annual","Other"],
 "resource_types": [...], "training_types": [...], "followup_methods": [...], "payment_statuses": [...], "discussion_stages": [...],
 "people": {"demo": ["Priya Sharma"], "mkt": [...], "acad": [...]},
 "distributors": [{"id":9,"name":"Royal Stationery Book Depot","phone":"9849244024"}],
 "role_labels": {"admin":"Admin", "...": "..."}
}
```

## Dashboard & search

* `GET /dashboard` → role-aware: `{"kpis":[{"group","label","value","link","tone"?}], "overdue":[item], "upcoming":[item], "my_work":[{"title","items":[item]}], "downloads_by_school":[...], "funnel":[{"label","value"}], "no_download_schools":[name], "pending_cancellations":[{"entity","id","ref","label","reason","by","at"}]}`
  `item` = `{"date","title","subtitle","link":{"screen","id"?}, "late"?:bool}`.
* `GET /nav-counts` → `{"counts":{screen: n}}` — menu badges, only non-zero, only screens the user can open:
  `requests` new, `marketing` overdue follow-ups, `orders` distributor orders to review, `myorders` returned orders,
  `training` sessions past their time still Scheduled, `papers` new paper requests, `acschools` orders missing academic support. School users get `{}`.
* `GET /search?q=` → `{"requests":[…],"trainings":[…],"papers":[…],"resources":[…]}`

## Demo requests (school pipeline)

* `GET /requests?q=&status=` → list items:
  `{"id","no","created_at","ay","status","order_status","school":{"id","name","city","state","board"},"distributor":{"id","name"},"assigned_to","pref_date","pref_time","cancelled","cancel_pending","direct"}`
* `POST /requests` body:
  `{"school":{"name","address","city","state","pincode","board","strength","contact","designation","mobile","email"},"ay","classes":[],"subjects":[],"series":[],"exp_qty","pref_date","pref_time","distributor_id"?,"remarks"}`
  (`distributor_id` required unless caller is a distributor.) → detail. 409 on duplicate school+city+ay.
* `GET /requests/<id>` → detail:
```json
{"id","no","created_at","ay","status","order_status","assigned_to","remarks","classes","subjects","series","exp_qty","pref_date","pref_time","direct",
 "school":{...}, "distributor":{"id","name","phone"},
 "notes":[{"at","by","type","text"}],
 "schedule":{"at","mode","presenter","marketing","platform","link","venue","agenda","instructions","shared_at","reminded"}|null,
 "feedback":{"by","date","attendees","designations","classes","subjects","series","interest","requirements","requested":[],"objections","competitor","next_follow","remarks","files":[file]}|null,
 "marketing":{"potential","dm_name","dm_desig","dm_mobile","dm_email","competitor","exp_qty","decision_date","stage","remarks","next_action","next_follow","person"}|null,
 "followups":[{"id","at","method","person","summary","next_action","next_date","by"}],
 "order":{"ay","po","series","classes","subjects","qty","conf_date","del_date","payment","remarks","source":"myjo|distributor"}|null,
 "dist_order":{"status":"Submitted|Returned|Rejected|Accepted","direct":bool,"ay","po","series","classes","subjects","qty","req_delivery","remarks","files":[file],"by","at","review_note","reviewed_by","reviewed_at"}|null,
 "academic":{"eligible":bool,"coverage":{"training":bool,"papers":bool,"resources":bool,"complete":bool,"missing":[..]},
             "trainings":[{"id","no","title","status","at"}],"papers":[{"id","no","status","cls","subject","exam"}],"resources_count":n,
             "pack":{"at","by","training_id","paper_ids":[],"resource_ids":[]}|null,"login":{"username","active"}|null}|null,
 "cancel":{"reason","by","at","approved_by"}|null, "cancelled": bool,
 "steps":[{"label","done":bool,"stopped":bool}],
 "audit":[audit]   // only for roles with seeInternal
 ,"actions":["edit","review","approve","reject","info","hold","resume","assign","schedule","share","feedback","marketing","followup","order","dist_order","dist_update","dist_confirm","accept_dist","return_dist","reject_dist","cancel"]}
```
  Distributors never receive `feedback`, `marketing`, `followups`, `audit`.
* `PUT /requests/<id>` — edit (same body as POST) while New / Under Review / On Hold.
* `POST /requests/<id>/review` · `/approve {"note"?}` · `/reject {"reason"}` · `/info {"reason"}` · `/hold {"reason"}` · `/resume` · `/assign {"assigned_to"}`
* `PUT /requests/<id>/schedule` `{"at","mode":"Online|Offline","presenter","marketing","platform","link","venue","agenda","instructions"}` → Demo Scheduled.
  `at` must be future; Online needs platform + https link; Offline needs venue.
* `POST /requests/<id>/share` → records `shared_at`, notifies school + distributor; returns `{"message": "text to copy/send"}`.
* `PUT /requests/<id>/feedback` `{"by","date","attendees","designations","classes","subjects","series","interest","requirements","requested","objections","competitor","next_follow","remarks","file_ids":[]}` → Demo Completed.
* `PUT /requests/<id>/marketing` `{...marketing fields}` → Follow-up Pending.
* `POST /requests/<id>/followups` `{"at","method","person","summary","next_action","next_date"}`
* `PUT /requests/<id>/order` (Marketing/Admin) `{"order_status", ...order fields, "pack":{...}}`
  `order fields` = `"ay","po","series","classes","subjects","qty","conf_date","del_date","payment","remarks"` (required when status is Order Confirmed / Partially Confirmed).
  `pack` (required when it converts the school) = `{"training_at","training_mode":"Offline|Online","teachers","venue"?,"link"?,"exams":[..],"papers_by"}`.
  Not Interested / Lost to Competitor → Not Converted (closes portal). Only Admin can move a Converted school back.
* `POST /requests/<id>/dist-order` (Distributor) body = order fields + `file_ids` + `pack`.
  With `directConfirm` permission the order is **final**: school Converted, login created, academic pack created. Without it → `dist_order.status = "Submitted"` for Marketing review (pack not required).
* `PUT /requests/<id>/dist-order` — distributor updates its own final order (order fields only).
* `POST /requests/<id>/dist-order/accept` (Marketing) body = order fields + pack (prefill from `dist_order`) · `/return {"reason"}` · `/reject {"reason"}`
* `POST /requests/<id>/cancel {"reason"}` → pending Admin approval.

* `POST /direct-orders` (Distributor) — new school + order in one call:
  `{"school":{...},"ay","order":{order fields + file_ids, "order_status"?},"pack":{...},"distributor_id"?}` → request detail + `message`.
  With `directConfirm` the order is final and `pack` is required (school converted, academic support set up).
  Without it, `pack` is ignored and the order is `Submitted` for Marketing to accept / return / reject.

## Marketing & orders

* `GET /followups?limit=25` → recent follow-ups across schools.
* `GET /marketing` → open schools (after demo, not final) with marketing summary.
* `GET /orders` → `{"confirmed":[{request_id, school, ay, distributor, series, classes, subjects, qty, po, conf_date, del_date, payment, order_status, source}], "pending_dist":[...], "totals":{"schools","books"}}`
* `GET /my-orders` (Distributor) → `{"can_order":[{id,school,city,status,dist_order_status}], "orders":[...], "kpis":{...}}`

## Academic

* `GET /ordered-schools` → `[{request_id, school, city, distributor, order:{status,source,date,po,qty,series,classes,subjects}, counts:{trainings,papers,resources}, coverage:{...}, login_active}]` (missing support first)

### Trainings (group sessions)
* `GET /trainings?status=` → `[{id,no,title,type,ay,at,mode,trainer,status,schools:[{request_id,name,expected,attended}],expected_total,attended_total,overdue,cancel_pending}]`
* `POST /trainings` `{"title","type","ay","series","classes","subjects","at","mode","trainer","link","venue","agenda","schools":[{"request_id","expected"}],"resource_ids","remarks","instructions","status":"Draft|Scheduled"}`
* `GET /trainings/<id>` → full incl. `schools:[{request_id,name,city,expected,school_confirm,school_teachers,attended,attendance,myjo_feedback,school_feedback:{rating,text,attended,by,at}|null}]`, `resources`, `completion`, `history`, `actions:["edit","schedule","complete","close","cancel"]`
* `PUT /trainings/<id>` (Draft/Scheduled) same body · `POST /trainings/<id>/schedule`
* `POST /trainings/<id>/complete` `{"status":"Completed|Partially completed","trainer_remarks","follow_up","recording","file_ids","resource_ids","schools":[{"request_id","attended","attendance","myjo_feedback"}]}`
* `POST /trainings/<id>/close {"note"?}` · `POST /trainings/<id>/cancel {"reason"}`

### Question papers
* `GET /papers?status=` → `[{id,no,request_id,school,ay,cls,subject,series,exam,due_date,assignee,max_marks,status,qp_file,ak_file,revoked,raised_by,overdue,cancel_pending,actions}]`
* `POST /papers` `{"request_id","ay","cls","subject","series","exam","due_date","assignee","max_marks","delivery_date","status","qp_file_id","ak_file_id","remarks"}`
* `PUT /papers/<id>` same · `POST /papers/<id>/publish` · `/deliver` · `/revoke {"reason"}` · `/restore` · `/cancel {"reason"}`

### Resources
* `GET /resources?status=` · `POST /resources` `{"title","type","series","cls","subject","ay","description","file_id","link","version","access":"All Ordered Schools|Selected Schools Only","school_ids":[],"status":"Draft|Published"}`
* `PUT /resources/<id>` · `POST /resources/<id>/publish` · `/archive` · `PUT /resources/<id>/access {"revoked_ids":[]}` · `/cancel {"reason"}`

### Files
* `POST /files` multipart `file` → `{"id","name","size","mime"}` (pdf, doc(x), ppt(x), xls(x), zip, jpg, png; max 50 MB)
* `GET /files/<id>/download?context=paper:<id>:qp|paper:<id>:ak|resource:<id>` → file stream. For school users access is checked against the context and the download is recorded.

### Downloads
* `GET /downloads?request_id=` → `{"by_school":[{request_id,school,papers,resources,last}], "log":[{at,school,user,kind,item,file}]}`

## School portal (role `school`)
* `GET /portal/overview` → `{school, order:{...,status}, upcoming_trainings, updates, kpis}`
* `GET /portal/trainings` → sessions for my school (not Draft) incl. my row + downloadable resources
* `POST /portal/trainings/<id>/confirm {"confirm":"Confirmed|Declined","teachers","note"}` · `POST /portal/trainings/<id>/feedback {"rating","attended","text"}`
* `GET /portal/library?cls=&subject=&series=&ay=&type=&exam=&q=` → `{"papers":[...],"resources":[...]}` (published, not revoked, my school only)
* `POST /portal/resources/<id>/open` → `{"link"}` for a video-link resource; records the view in download history (file resources use `GET /files/<id>/download?context=resource:<id>`)
* `POST /portal/papers` `{"ay","series","cls","subject","exam","due_date","max_marks","remarks"}` · `GET /portal/requests` (my paper requests)
* `GET /portal/history` → my school's downloads

## Admin
* `GET /users` · `POST /users {"name","username","email","phone","role","org"?,"school_request_id"?,"temp_password","temp_pin"}` · `PUT /users/<id>` · `POST /users/<id>/toggle {"reason"}` · `POST /users/<id>/reset {"temp_password","temp_pin"}`
* `GET /permissions` → `{"roles":[..],"screens":[{code,label,eligible:{role:bool}}],"actions":[{code,label,eligible:{role:bool}}],"granted":{"screens":{role:[codes]},"actions":{role:[codes]}}}`
* `PUT /permissions` `{"role","kind":"screen|action","code","granted":bool}` · `POST /permissions/reset`
* `GET /masters` → `{"series":[{id,name,color,active,used}],"subjects":[{id,name,active,used}]}` · `POST /masters/<kind>` · `PUT /masters/<kind>/<id>` · `POST /masters/<kind>/<id>/toggle` · `DELETE /masters/<kind>/<id>` (only when unused) — `kind` = `series|subjects`
* `GET /cancellations` (pending) · `POST /cancellations/<entity>/<id>/approve` · `/decline` — `entity` = `request|training|paper|resource`
* `GET /audit?q=&entity=&limit=300`
* `GET /notifications?limit=150` · `POST /reminders/run` → `{"sent": n}`

## Reports
* `GET /reports` → `[{key,name}]` (17)
* `GET /reports/<key>?from=&to=&school=&distributor=&city=&state=&ay=&series=&cls=&subject=&status=&employee=&marketing=&presenter=&trainer=` → `{"name","columns":[{"label","type":"text|number"}],"rows":[[..]],"total":[..]|null}`
* `GET /reports/<key>/export?format=xlsx|pdf|csv&…filters` → file download
