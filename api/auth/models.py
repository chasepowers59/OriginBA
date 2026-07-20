"""Identity models — hosted separately from CISADM / Oracle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.auth.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "portal_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, default="demo")
    organization_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    group_links: Mapped[list[UserAccessGroup]] = relationship(
        "UserAccessGroup",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AccessGroup(Base):
    __tablename__ = "portal_access_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, default="demo")
    # Comma-separated workstream ids, or "*" for all workstreams.
    workstreams_csv: Mapped[str] = mapped_column(String(512), nullable=False, default="*")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    members: Mapped[list[UserAccessGroup]] = relationship(
        "UserAccessGroup",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    def workstream_ids(self) -> list[str]:
        raw = (self.workstreams_csv or "*").strip()
        if raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]


class AuditLog(Base):
    __tablename__ = "portal_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, default="demo")
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_email: Mapped[str] = mapped_column(String(320), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class UserAccessGroup(Base):
    __tablename__ = "portal_user_access_groups"
    __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_user_group"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("portal_users.id", ondelete="CASCADE"))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("portal_access_groups.id", ondelete="CASCADE"))

    user: Mapped[User] = relationship("User", back_populates="group_links")
    group: Mapped[AccessGroup] = relationship("AccessGroup", back_populates="members")
