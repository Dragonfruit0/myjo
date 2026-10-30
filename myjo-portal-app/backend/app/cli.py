"""Flask CLI: `flask --app wsgi init-db`, `seed`, `send-reminders`, `export-schema`."""
import click
from flask import g


def register(app):
    @app.cli.command("init-db")
    @click.option("--drop", is_flag=True, help="Drop all tables first (destroys data).")
    def init_db(drop):
        """Create tables, default access rights and master lists."""
        from .extensions import db
        if drop:
            db.drop_all()
        db.create_all()
        seed_reference()
        db.session.commit()
        click.echo("Database ready.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--phone", prompt=True)
    @click.password_option()
    def create_admin(name, username, email, phone, password):
        """Create the first Admin account (asked to set a PIN at first sign-in)."""
        from .extensions import db
        from .models import User
        from .security import hash_secret, password_problem
        e = password_problem(password)
        if e:
            raise click.ClickException(e)
        db.session.add(User(name=name, username=username.lower(), email=email.lower(), phone=phone, role="admin",
                            pw_hash=hash_secret(password), must_change=True))
        db.session.commit()
        click.echo(f"Admin {username} created.")

    @app.cli.command("seed")
    def seed_cmd():
        """Load the sample data used in the prototype (for demos and testing)."""
        from .seed import seed_sample
        seed_sample()
        click.echo("Sample data loaded. Every sample account uses temporary password Myjo@123 and PIN 2580.")

    @app.cli.command("send-reminders")
    def send_reminders():
        """Run from cron, e.g. every 15 minutes."""
        from .api.admin import run_reminders
        from .extensions import db
        with app.test_request_context():
            g.user = None
            n = run_reminders()
            db.session.commit()
        click.echo(f"{n} reminder(s) sent.")

    @app.cli.command("export-schema")
    @click.argument("path", default="../db/schema.sql")
    def export_schema(path):
        """Write MySQL CREATE TABLE statements for all models."""
        from sqlalchemy.dialects import mysql
        from sqlalchemy.schema import CreateIndex, CreateTable
        from .extensions import db
        out = ["-- Myjo School Demo, Order & Academic Support Portal · MySQL 8 schema",
               "-- Generated from the SQLAlchemy models (flask --app wsgi export-schema).",
               "SET NAMES utf8mb4;", "SET FOREIGN_KEY_CHECKS = 0;", ""]
        for t in db.metadata.sorted_tables:
            ddl = str(CreateTable(t).compile(dialect=mysql.dialect())).strip()
            out.append(ddl + " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n")
            for ix in t.indexes:
                out.append(str(CreateIndex(ix).compile(dialect=mysql.dialect())).strip() + ";")
            out.append("")
        out.append("SET FOREIGN_KEY_CHECKS = 1;")
        with open(path, "w") as fh:
            fh.write("\n".join(out))
        click.echo(f"Schema written to {path}")


def seed_reference():
    """Default permissions, book series and subjects (idempotent)."""
    from .api.admin import reset_permissions
    from .extensions import db
    from .models import Permission, Series, Subject
    if not Permission.query.first():
        reset_permissions()
    if not Series.query.first():
        for n, c in [("Myjo Maths Pathways", "#1A73C9"), ("Myjo English Reader", "#D81B60"), ("Myjo Science Explorer", "#1E8E3E"),
                     ("Myjo EVS Discovery", "#8B6A3E"), ("Myjo Hindi Vatika", "#F07D1A"), ("Myjo Computer Smart", "#7B2E8E")]:
            db.session.add(Series(name=n, color=c, active=True))
    if not Subject.query.first():
        for n in ["English", "Hindi", "Mathematics", "Science", "EVS", "Social Science", "Computer Science", "General Knowledge", "Urdu"]:
            db.session.add(Subject(name=n, active=True))
