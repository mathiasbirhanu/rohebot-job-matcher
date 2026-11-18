from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class EmployerRegistration(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    organization_name: str = Field(min_length=2, max_length=180)
    hr_first_name: str = Field(min_length=1, max_length=60)
    hr_middle_name: str = Field(min_length=1, max_length=60)
    hr_last_name: str = Field(min_length=1, max_length=60)
    phone: str = Field(min_length=4, max_length=40)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    role: str = Field(pattern="^(candidate|employer|admin)$")


class RecordCreate(BaseModel):
    payload: dict

    @field_validator("payload")
    @classmethod
    def require_payload(cls, value: dict) -> dict:
        if not value:
            raise ValueError("A non-empty payload is required.")
        return value


class RecordUpdate(BaseModel):
    payload: dict

    @field_validator("payload")
    @classmethod
    def require_payload(cls, value: dict) -> dict:
        if not value:
            raise ValueError("A non-empty payload is required.")
        return value


class EmailCreate(BaseModel):
    to: EmailStr
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    link: str | None = Field(default=None, max_length=1000)
    type: str = Field(min_length=1, max_length=40)


class CandidateInvitationRegistration(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    second_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=4, max_length=40)
    password: str = Field(min_length=12, max_length=128)


class JobRead(BaseModel):
    id: UUID
    employer_id: UUID
    title: str
    description: str
    location: str
    employment_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobList(BaseModel):
    items: list[JobRead]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
