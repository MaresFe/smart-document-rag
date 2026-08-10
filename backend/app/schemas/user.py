from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class FullNameMixin(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(value.split())
        return normalized or None


class UserRegister(FullNameMixin):
    email: EmailStr
    password: str = Field(
        min_length=10,
        max_length=128,
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=1,
        max_length=128,
    )


class InvitationCreate(BaseModel):
    email: EmailStr


class InvitationTokenRequest(BaseModel):
    token: str = Field(
        min_length=32,
        max_length=512,
    )


class InvitationPreview(BaseModel):
    email: EmailStr
    expires_at: datetime


class InvitationAccept(FullNameMixin):
    token: str = Field(
        min_length=32,
        max_length=512,
    )
    password: str = Field(
        min_length=10,
        max_length=128,
    )


class InvitationRead(BaseModel):
    id: UUID
    email: EmailStr
    expires_at: datetime
    created_at: datetime
    delivery_mode: str
    invitation_url: str | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetTokenRequest(BaseModel):
    token: str = Field(
        min_length=32,
        max_length=512,
    )


class PasswordResetPreview(BaseModel):
    expires_at: datetime


class PasswordResetConfirm(PasswordResetTokenRequest):
    password: str = Field(
        min_length=10,
        max_length=128,
    )


class PasswordResetRequestRead(BaseModel):
    message: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_admin: bool
    email_verified_at: datetime | None
    created_at: datetime
