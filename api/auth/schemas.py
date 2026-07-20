"""Pydantic schemas for auth API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email:
            raise ValueError("Invalid email")
        return email


class PortalOrganizationPublic(BaseModel):
    id: str
    display_name: str


class AuthUserPublic(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    client_id: str
    organization_id: str | None = None
    organization_name: str | None = None
    is_active: bool
    must_change_password: bool = False
    workstreams: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)
    group_names: list[str] = Field(default_factory=list)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: AuthUserPublic


class AuthStatusResponse(BaseModel):
    enabled: bool
    authenticated: bool = False


class AccessGroupPublic(BaseModel):
    id: str
    name: str
    description: str
    client_id: str
    workstreams: list[str]
    member_count: int = 0


class AccessGroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    workstreams: list[str] = Field(default_factory=lambda: ["*"])


class AccessGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    workstreams: list[str] | None = None


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="user", pattern="^(user|editor|admin)$")
    organization_id: str | None = Field(default=None, min_length=2, max_length=64)
    group_ids: list[str] = Field(default_factory=list)
    is_active: bool = True


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    role: str | None = Field(default=None, pattern="^(user|editor|admin)$")
    organization_id: str | None = Field(default=None, min_length=2, max_length=64)
    group_ids: list[str] | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
