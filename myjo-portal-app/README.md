# Myjo School Demo, Order & Academic Support Portal

Production codebase for Myjo Publications. It covers the whole school journey:
distributor demo request → review → online/offline demo → feedback → marketing follow-up →
book order → automatic academic support (group teacher training, question papers, teaching manuals) → school portal.

| Layer | Technology |
|---|---|
| Database | MySQL 8 (utf8mb4) |
| API | Python 3.11+, Flask 3, SQLAlchemy 2, PyMySQL, JWT |
| Front end | React 18 + TypeScript, built with Vite on Node.js 20 |
| Serving | gunicorn (API) behind nginx (static app + `/api` proxy) |

```
backend/     Flask API (app/), tests/, Dockerfile
frontend/    React + TypeScript app
db/          schema.sql (MySQL DDL, generated from the models)
docs/        API.md (REST contract)
deploy/      nginx.conf, web.Dockerfile
docker-compose.yml, .env.example
```

---

## 1. Quick start with Docker (recommended)

Requires Docker with the Compose plugin.

```bash
cp .env.example .env
# edit .env: set SECRET_KEY, MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD
docker compose up -d --build

# first time only: create tables
docker compose exec api flask --app wsgi init-db

# EITHER create your real Admin account …
docker compose exec api flask --app wsgi create-admin
# … OR load the sample data for a demo / training
docker compose exec api flask --app wsgi seed
```

Open **http://SERVER:8080** (change `WEB_PORT` in `.env`).
For HTTPS, put the server behind your usual TLS proxy (Caddy, nginx, a cloud load balancer).

### Daily reminders
Follow-up and paper-deadline reminders are sent by a command. Run it once a day from the host's cron:

```cron
30 8 * * *  cd /opt/myjo-portal-app && docker compose exec -T api flask --app wsgi send-reminders
```

It is safe to run more than once a day; a reminder is sent only once per item per day.
Admin can also run it from **Notifications → Run reminders now**.

### Backups
```bash
docker compose exec db sh -c 'mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" myjo_portal' > myjo-$(date +%F).sql
docker run --rm -v myjo-portal-app_uploads:/u -v "$PWD":/b alpine tar czf /b/uploads-$(date +%F).tgz -C /u .
```
Back up both: the database holds the records, and the uploads volume holds the question papers and manuals.

---

## 2. Running without Docker (development)

### Database
```sql
CREATE DATABASE myjo_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'myjo'@'localhost' IDENTIFIED BY 'choose-a-password';
GRANT ALL ON myjo_portal.* TO 'myjo'@'localhost';
```

### API (Flask)
```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="mysql+pymysql://myjo:choose-a-password@127.0.0.1:3306/myjo_portal?charset=utf8mb4"
export SECRET_KEY="dev-only-secret"
flask --app wsgi init-db
flask --app wsgi seed            # sample data (optional)
flask --app wsgi run --debug     # http://localhost:5000/api/health
```

### Front end (React + TypeScript)
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to :5000)
npm run typecheck
npm run build      # production files in frontend/dist
```

### CLI commands
| Command | Purpose |
|---|---|
| `flask --app wsgi init-db [--drop]` | Create tables and reference data (roles, permissions, 6 series, 9 subjects incl. Urdu). `--drop` wipes everything first. |
| `flask --app wsgi create-admin` | Create an Admin login interactively. |
| `flask --app wsgi seed` | Load sample schools, orders, trainings, papers and users. |
| `flask --app wsgi send-reminders` | Send due follow-up and paper reminders. |
| `flask --app wsgi export-schema db/schema.sql` | Regenerate the MySQL DDL. |

---

## 3. Sample logins (after `seed`)

Every sample account starts with the temporary password **Myjo@123** and PIN **2580**.
On first sign-in the user must set their own password (8+ characters with letters and numbers) and a 4-digit PIN.
Pick the designation first; the account must belong to it.

| Designation | Username | Name |
|---|---|---|
| Admin | `syed.sufiyan` | Syed Sufiyan |
| Management | `nuzhat.khan` | Nuzhat Khan |
| Demo Team | `priya.sharma`, `karthik.iyer` | |
| Marketing Team | `neha.gupta`, `arjun.rao` | |
| Academic Team | `meera.nair`, `sameer.joshi` | |
| Distributor | `royalstationery` | Royal Stationery Book Depot (+91 98492 44024) |
| School | `dps.wagholi`, `stxaviers.navrangpura`, `sunrise.kondapur` | |

**Do not run `seed` on the live database.** Use `create-admin`, then add real users under **Users**.

---

## 4. Key behaviour

* **Classes** Nursery, LKG, UKG, 1–5. **Quantities** are whole numbers only; there are no book values.
* **Roles and access control.** Admin decides which screens and actions each designation gets (**Access control**). Admin always has everything. The API enforces every rule; the UI only hides buttons the API would refuse.
* **Distributor orders are final.** With the *Confirm orders directly* permission (on by default), a distributor order converts the school at once. It also sets up academic support: a group training session, a question paper for every class × subject × exam, shared teaching manuals, and the school's login. Without that permission, orders go to Marketing to accept, return or reject.
* **New school in one step.** A distributor can add a school and its order together (**My orders → Create order → + New school**). With direct confirmation the order is final at once; without it, the order goes to Marketing for review.
* **Menu badges** show what is waiting for each user: new requests, overdue follow-ups, distributor orders to review, returned orders, overdue training sessions, new paper requests, and orders missing academic support.
* **Every order has academic support.** An order cannot be confirmed without the training and question-paper details.
* **Group training.** A session covers several schools; there are no individual training requests. Drafts (e.g. online with no link yet) do **not** count as training coverage.
* **Conversion %** counts only schools that had a demo. Direct distributor orders are reported separately, so the rate never exceeds 100%.
* **Lost / Not Interested / rejected orders** close the school portal and deactivate the school login.
* **Purchase-order numbers** are unique across Myjo and distributor orders (case-insensitive).
* **Audit trail.** Every change is stored with old and new values, the user and the time. It can't be edited.
* **Cancellation instead of delete.** Requests, trainings and papers are cancelled with a reason, and Admin approves. Records are kept.
* **Sign-in security.** Passwords and PINs are stored as salted PBKDF2 hashes. 5 wrong attempts lock the account for 5 minutes, and Admin can reset it. Tokens expire after `TOKEN_HOURS`.
* **Notifications** are always stored. With `SEND_MESSAGES=1` and SMTP / WhatsApp Cloud API settings, they are also sent by email and WhatsApp.

The full REST contract is in [docs/API.md](docs/API.md).

---

## 5. Tests

```bash
cd backend
# against MySQL (recommended: same engine as production)
mysql -u root -p -e "CREATE DATABASE myjo_test CHARACTER SET utf8mb4; GRANT ALL ON myjo_test.* TO 'myjo'@'localhost';"
TEST_DATABASE_URL="mysql+pymysql://myjo:PASSWORD@127.0.0.1:3306/myjo_test?charset=utf8mb4" pytest -q
# quick run on in-memory SQLite
pytest -q
```

The suite covers:
* sign-in, lockout, PIN and first-time setup;
* role isolation and school data isolation;
* the full request → demo → order → academic pipeline with validation;
* distributor final, review-mode and one-step orders;
* group training, papers, resources, uploads and downloads;
* all 17 reports, with xlsx/pdf/csv export;
* masters, users, audit, reminders and search;
* regression checks for defects D1–D6 from the prototype test report.

Browser tests (Playwright) for every role and screen, the distributor order → school portal flow, and the review-mode new-school flow with menu badges are in [e2e/](e2e/README.md).

**`myjo_test` is wiped on every run**, so never point `TEST_DATABASE_URL` at the live database.
