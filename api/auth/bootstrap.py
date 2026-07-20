"""Initialize identity database tables and seed default admin."""

from __future__ import annotations

from sqlalchemy import func, inspect, select, text

from api.auth.config import auth_disabled, bootstrap_admin_email, bootstrap_admin_password
from api.auth.database import Base, get_engine, get_session_factory
from api.auth.models import AccessGroup, User
from api.auth.security import hash_password
from api.portal_config import load_portal_config


def _migrate_schema(engine) -> None:
    inspector = inspect(engine)
    if "portal_users" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("portal_users")}
    migrations: list[str] = []
    if "must_change_password" not in columns:
        migrations.append(
            "ALTER TABLE portal_users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"
        )
    if "organization_id" not in columns:
        migrations.append("ALTER TABLE portal_users ADD COLUMN organization_id VARCHAR(64)")
    for stmt in migrations:
        with engine.begin() as conn:
            conn.execute(text(stmt))


def init_auth_database() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_schema(engine)

    if auth_disabled():
        return

    factory = get_session_factory()
    with factory() as session:
        count = session.scalar(select(func.count()).select_from(User))
        if count and count > 0:
            bootstrap_email = bootstrap_admin_email().lower()
            admin = session.scalar(select(User).where(func.lower(User.email) == bootstrap_email))
            if admin and admin.last_login_at is None:
                admin.must_change_password = True
                session.add(admin)
                session.commit()
            return

        client_id = load_portal_config().get("client_id", "demo")
        admin = User(
            email=bootstrap_admin_email(),
            display_name="Portal Administrator",
            password_hash=hash_password(bootstrap_admin_password()),
            role="admin",
            client_id=client_id,
            organization_id="demo",
            is_active=True,
            must_change_password=True,
        )
        session.add(admin)
        session.flush()

        default_group = AccessGroup(
            name="All workstreams",
            description="Full analytics access across all governed workstreams.",
            client_id=client_id,
            workstreams_csv="*",
        )
        session.add(default_group)
        session.commit()
