import secrets
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Annotated
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from sqlalchemy import or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.core.config import settings
from app.core.security import hash_password, hash_token, new_session_token, verify_password
from app.db.session import get_db
from app.email_delivery import deliver_email
from app.models import (
    AccountVerification,
    ApplicationRecord,
    CandidateDocument,
    CandidateProfile,
    CandidateInvitation,
    EmailOutbox,
    EmployerProfile,
    Job,
    JobApplication,
    TrainerQrSettings,
    TrainerRegistration,
    User,
    UserSession,
)
from app.schemas import (
    CandidateInvitationRegistration,
    EmailCreate,
    EmployerRegistration,
    JobList,
    LoginRequest,
    RecordCreate,
    RecordUpdate,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_role("admin"))]
EmployerUser = Annotated[User, Depends(require_role("employer"))]
CandidateUser = Annotated[User, Depends(require_role("candidate"))]

RESOURCE_NAMES = {
    "audit-logs",
    "career-enrollments",
    "certificates",
    "courses",
    "decline-records",
    "email-outbox",
    "feedback",
    "invitations",
    "interviews",
    "notifications",
    "placements",
    "reviews",
    "saved-candidates",
    "skills-gap",
    "subscriptions",
    "transactions",
    "trainer-settings",
    "trainer-emails",
    "trainers",
    "verifications",
}


@router.get("/health")
def health_check(db: DbSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="Database is unavailable") from error
    return {"status": "ok", "database": "ok"}


@router.get("/invitations/{token}")
def inspect_candidate_invitation(token: str, db: DbSession) -> dict[str, bool | str]:
    invitation = db.scalar(
        select(CandidateInvitation).where(
            CandidateInvitation.token_hash == hash_token(token),
            CandidateInvitation.expires_at > datetime.now(timezone.utc),
            CandidateInvitation.used_at.is_(None),
            CandidateInvitation.revoked_at.is_(None),
        )
    )
    return {
        "valid": bool(invitation),
        "message": "Invitation is valid." if invitation else "This invitation link is invalid or expired.",
    }


@router.post("/invitations/{token}/register", status_code=201)
def register_invited_candidate(
    token: str,
    data: CandidateInvitationRegistration,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> dict[str, str | bool]:
    invitation = db.scalar(
        select(CandidateInvitation).where(
            CandidateInvitation.token_hash == hash_token(token),
            CandidateInvitation.expires_at > datetime.now(timezone.utc),
            CandidateInvitation.used_at.is_(None),
            CandidateInvitation.revoked_at.is_(None),
        ).with_for_update()
    )
    if not invitation:
        raise HTTPException(status_code=400, detail="This invitation link is invalid or expired.")

    email = str(data.email).strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    full_name = f"{data.first_name.strip()} {data.second_name.strip()}"
    account = User(email=email, password_hash=hash_password(data.password), role="candidate", is_active=False)
    db.add(account)
    try:
        db.flush()
        db.add(
            CandidateProfile(
                user_id=account.id,
                full_name=full_name,
                phone=data.phone.strip(),
                status="Pending OTP",
                profile_data={"emailVerified": False},
            )
        )
        db.add(
            AccountVerification(
                user_id=account.id,
                code_hash=hash_token(code),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        outbox_email = EmailOutbox(
            recipient=email,
            subject="Verify your Rohobot Candidate Account",
            body=f"Your development verification code is {code}. It expires in 10 minutes.",
            category="email_verification",
        )
        db.add(outbox_email)
        invitation.used_at = datetime.now(timezone.utc)
        db.commit()
        background_tasks.add_task(deliver_email, outbox_email.id)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from error

    return {"success": True, "message": "Account created. Verify your email before signing in."}


@router.get("/training")
def get_training_data(
    db: DbSession,
    user: AdminUser,
    view: str | None = None,
) -> dict:
    if view == "scan":
        settings_row = db.get(TrainerQrSettings, 1)
        expires_at = settings_row.expires_at if settings_row else None
        active = bool(settings_row and settings_row.active)
        if expires_at and expires_at <= datetime.now(timezone.utc):
            active = False
        return {
            "active": active,
            "expiresAt": expires_at.isoformat() if expires_at else None,
            "registrationUrl": f"{settings.frontend_base_url.rstrip('/')}/trainer/scan",
        }
    trainers = db.scalars(
        select(TrainerRegistration).order_by(TrainerRegistration.registered_at.desc())
    ).all()
    return {
        "trainers": [
            {
                "id": str(trainer.id),
                "fullName": trainer.full_name,
                "email": trainer.email,
                "emailVerified": trainer.email_verified,
                "trainingCompleted": trainer.training_completed,
                "invitationSent": trainer.invitation_sent,
                "profileCreated": trainer.profile_created,
                "registeredAt": trainer.registered_at.isoformat(),
            }
            for trainer in trainers
        ]
    }


@router.patch("/training")
def update_training_qr(data: dict, user: AdminUser, db: DbSession) -> dict:
    expires_at = data.get("expiresAt")
    parsed_expiry = None
    if expires_at:
        try:
            parsed_expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Expiration time must be a valid ISO date.") from error
    if not isinstance(data.get("active"), bool):
        raise HTTPException(status_code=422, detail="Choose whether the QR registration is active.")
    if data["active"] and not parsed_expiry:
        raise HTTPException(status_code=422, detail="Set an expiration time before activating registration.")
    row = db.get(TrainerQrSettings, 1)
    if not row:
        row = TrainerQrSettings(id=1)
        db.add(row)
    row.active = data["active"]
    row.expires_at = parsed_expiry
    db.commit()
    return {
        "success": True,
        "settings": {"active": row.active, "expiresAt": row.expires_at.isoformat() if row.expires_at else None},
    }


@router.post("/training/verify")
def verify_trainer_email(token: str, db: DbSession) -> dict[str, str | bool]:
    trainer = db.scalar(
        select(TrainerRegistration).where(
            TrainerRegistration.verify_token_hash == hash_token(token),
            TrainerRegistration.verify_expires_at > datetime.now(timezone.utc),
        )
    )
    if not trainer:
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired.")
    trainer.email_verified = True
    trainer.verify_token_hash = None
    trainer.verify_expires_at = None
    db.commit()
    return {"success": True, "message": "Your email has been verified."}


@router.post("/training")
def training_action(data: dict, db: DbSession, background_tasks: BackgroundTasks) -> dict:
    action = data.get("action")
    if action == "register":
        settings_row = db.get(TrainerQrSettings, 1)
        if (
            not settings_row
            or not settings_row.active
            or not settings_row.expires_at
            or settings_row.expires_at <= datetime.now(timezone.utc)
        ):
            raise HTTPException(status_code=404, detail="Trainer registration is currently unavailable.")
        first = str(data.get("firstName") or "").strip()
        middle = str(data.get("middleName") or "").strip()
        last = str(data.get("lastName") or "").strip()
        email = str(data.get("email") or "").strip().lower()
        if not first or not middle or not last or len(first) > 60 or len(middle) > 60 or len(last) > 60:
            raise HTTPException(status_code=422, detail="Enter first, middle, and last names up to 60 characters each.")
        if "@" not in email or len(email) > 320:
            raise HTTPException(status_code=422, detail="Enter a valid email address.")
        if db.scalar(select(TrainerRegistration.id).where(TrainerRegistration.email == email)):
            raise HTTPException(status_code=409, detail="This trainer email is already registered.")
        token = new_session_token()
        trainer = TrainerRegistration(
            full_name=f"{first} {middle} {last}",
            email=email,
            verify_token_hash=hash_token(token),
            verify_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(trainer)
        link = f"{settings.frontend_base_url.rstrip('/')}/trainer/verify?token={token}"
        outbox_email = EmailOutbox(
            recipient=email,
            subject="Verify your Rohobot Training Account",
            body=f"Verify your email using this link: {link}",
            category="email_verification",
            link=link,
        )
        db.add(outbox_email)
        db.commit()
        background_tasks.add_task(deliver_email, outbox_email.id)
        result = {"success": True, "message": "Verification email recorded in the local email outbox."}
        if settings.environment == "development":
            result["verificationLink"] = link
        return result

    user_session = None
    session_token = request.cookies.get("rohobot_session")
    if session_token:
        user_session = db.scalar(
            select(UserSession).where(
                UserSession.token_hash == hash_token(session_token),
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
    admin_user = db.get(User, user_session.user_id) if user_session else None
    if not admin_user or not admin_user.is_active or admin_user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")

    if action == "complete":
        try:
            trainer_id = UUID(str(data.get("trainerId")))
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Choose a valid trainer.") from error
        trainer = db.get(TrainerRegistration, trainer_id)
        if not trainer or not trainer.email_verified:
            raise HTTPException(status_code=404, detail="Verified trainer not found.")
        if trainer.profile_created:
            raise HTTPException(status_code=409, detail="This trainer already has a candidate account.")
        token = new_session_token()
        trainer.training_completed = True
        trainer.invitation_sent = True
        trainer.invite_token_hash = hash_token(token)
        trainer.invite_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        link = f"{settings.frontend_base_url.rstrip('/')}/candidate/register?token={token}"
        outbox_email = EmailOutbox(
            recipient=trainer.email,
            subject="Create your Rohobot profile",
            body=f"Your training is complete. Create your account: {link}",
            category="training_invitation",
            link=link,
        )
        db.add(outbox_email)
        db.commit()
        background_tasks.add_task(deliver_email, outbox_email.id)
        result = {"success": True, "message": "Invitation recorded in the local email outbox."}
        if settings.environment == "development":
            result["invitationLink"] = link
        return result

    if action == "inspect":
        trainer = db.scalar(
            select(TrainerRegistration).where(
                TrainerRegistration.invite_token_hash == hash_token(str(data.get("token") or "")),
                TrainerRegistration.invite_expires_at > datetime.now(timezone.utc),
                TrainerRegistration.profile_created.is_(False),
            )
        )
        if not trainer:
            return {"valid": False, "message": "This invitation link is invalid or expired."}
        return {"valid": True, "fullName": trainer.full_name, "email": trainer.email}

    if action == "signup":
        token = str(data.get("token") or "")
        phone = str(data.get("phone") or "").strip()
        password = str(data.get("password") or "")
        trainer = db.scalar(
            select(TrainerRegistration).where(
                TrainerRegistration.invite_token_hash == hash_token(token),
                TrainerRegistration.invite_expires_at > datetime.now(timezone.utc),
                TrainerRegistration.profile_created.is_(False),
            )
        )
        if not trainer:
            raise HTTPException(status_code=400, detail="This invitation link is invalid or expired.")
        if len(phone) < 4 or len(phone) > 40 or len(password) < 12 or len(password) > 128:
            raise HTTPException(status_code=422, detail="Enter a valid phone number and a password of at least 12 characters.")
        if db.scalar(select(User.id).where(User.email == trainer.email)):
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        account = User(email=trainer.email, password_hash=hash_password(password), role="candidate", is_active=True)
        db.add(account)
        db.flush()
        db.add(
            CandidateProfile(
                user_id=account.id,
                full_name=trainer.full_name,
                phone=phone,
                status="Pending Review",
                profile_data={"emailVerified": True},
            )
        )
        trainer.phone = phone
        trainer.profile_created = True
        trainer.invite_token_hash = None
        trainer.invite_expires_at = None
        db.commit()
        return {"success": True, "message": "Candidate account created. Sign in to complete your profile."}

    raise HTTPException(status_code=422, detail="Invalid trainer action.")


@router.post("/auth/register/employer", status_code=201)
def register_employer(
    data: EmployerRegistration, db: DbSession, background_tasks: BackgroundTasks
) -> dict:
    email = str(data.email).strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(email=email, password_hash=hash_password(data.password), role="employer", is_active=False)
    db.add(user)
    try:
        db.flush()
        db.add(
            EmployerProfile(
                user_id=user.id,
                organization_name=data.organization_name.strip(),
                phone=data.phone.strip(),
                status="Pending OTP",
                profile_data={
                    "hrFirstName": data.hr_first_name.strip(),
                    "hrMiddleName": data.hr_middle_name.strip(),
                    "hrLastName": data.hr_last_name.strip(),
                    "orgEmail": email,
                    "orgPhone": data.phone.strip(),
                    "paymentSubmitted": False,
                },
            )
        )
        code = f"{secrets.randbelow(1_000_000):06d}"
        db.add(
            AccountVerification(
                user_id=user.id,
                code_hash=hash_token(code),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        outbox_email = EmailOutbox(
            recipient=email,
            subject="Verify your Rohobot Employer Account",
            body=f"Your development verification code is {code}. It expires in 10 minutes.",
            category="email_verification",
        )
        db.add(outbox_email)
        db.commit()
        background_tasks.add_task(deliver_email, outbox_email.id)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from error

    result = {
        "success": True,
        "userId": str(user.id),
        "message": "Verification code recorded in the local email outbox.",
    }
    if settings.environment == "development":
        result["testOtp"] = code
    return result


@router.post("/auth/request-verification")
def request_email_verification(
    role: str, email: str, db: DbSession, background_tasks: BackgroundTasks
) -> dict[str, bool | str]:
    if role not in {"candidate", "employer"}:
        raise HTTPException(status_code=422, detail="Choose a valid account role.")
    user = db.scalar(
        select(User).where(User.role == role, User.email == email.strip().lower())
    )
    if not user:
        raise HTTPException(status_code=404, detail="No account was found for this email.")
    if user.is_active:
        raise HTTPException(status_code=409, detail="This account is already verified.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    verification = db.scalar(
        select(AccountVerification)
        .where(AccountVerification.user_id == user.id)
        .order_by(AccountVerification.created_at.desc())
    )
    if verification:
        verification.code_hash = hash_token(code)
        verification.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        verification.attempts = 0
    else:
        db.add(
            AccountVerification(
                user_id=user.id,
                code_hash=hash_token(code),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
    outbox_email = EmailOutbox(
        recipient=user.email,
        subject=f"Verify your Rohobot {role.title()} Account",
        body=f"Your development verification code is {code}. It expires in 10 minutes.",
        category="email_verification",
    )
    db.add(outbox_email)
    db.commit()
    background_tasks.add_task(deliver_email, outbox_email.id)
    return {
        "success": True,
        "message": "A verification code has been recorded in the local email outbox.",
    }


@router.post("/auth/verify-email")
def verify_employer_email(
    code: str,
    db: DbSession,
    email: str | None = None,
    user_id: UUID | None = None,
    role: str = "employer",
) -> dict[str, bool]:
    if not email and not user_id:
        raise HTTPException(status_code=422, detail="Email or account ID is required.")
    if role not in {"candidate", "employer"}:
        raise HTTPException(status_code=422, detail="Choose a valid account role.")
    statement = select(User).where(User.role == role)
    if email:
        statement = statement.where(User.email == email.strip().lower())
    if user_id:
        statement = statement.where(User.id == user_id)
    user = db.scalar(statement)
    if not user:
        raise HTTPException(status_code=404, detail=f"No unverified {role} account was found.")
    verification = db.scalar(
        select(AccountVerification)
        .where(
            AccountVerification.user_id == user.id,
            AccountVerification.expires_at > datetime.now(timezone.utc),
        )
        .order_by(AccountVerification.created_at.desc())
    )
    if not verification or verification.attempts >= 5:
        raise HTTPException(status_code=400, detail="The verification code expired. Register again.")
    if not secrets.compare_digest(verification.code_hash, hash_token(code)):
        verification.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="The verification code is incorrect.")

    user.is_active = True
    if role == "employer":
        employer = db.get(EmployerProfile, user.id)
        if employer:
            employer.status = "Profile Incomplete"
    else:
        candidate = db.get(CandidateProfile, user.id)
        if candidate:
            candidate.status = "Pending Review"
            candidate.profile_data = {**candidate.profile_data, "emailVerified": True}
    db.delete(verification)
    db.commit()
    return {"success": True}


@router.post("/auth/login")
def login(data: LoginRequest, request: Request, response: Response, db: DbSession) -> dict:
    email = str(data.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if (
        not user
        or user.role != data.role
        or not user.is_active
        or not verify_password(data.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Email/password is incorrect, or the account is not verified.")

    token = new_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    db.add(UserSession(token_hash=hash_token(token), user_id=user.id, expires_at=expires_at))
    db.commit()

    if user.role == "candidate":
        access_state = "active"
        destination = "/candidate"
    elif user.role == "employer":
        employer = db.get(EmployerProfile, user.id)
        status = employer.status if employer else "Pending OTP"
        access_state = (
            "active"
            if status == "Active"
            else "payment-pending"
            if status == "Pending Admin Review"
            else "needs-payment"
        )
        destination = (
            "/employer"
            if access_state == "active"
            else "/employer/pending"
            if access_state == "payment-pending"
            else "/employer/setup"
        )
    else:
        access_state = "active"
        destination = "/admin"

    secure = request.url.scheme == "https"
    cookie_options = {
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "path": "/",
        "max_age": settings.session_ttl_hours * 3600,
    }
    response.set_cookie("rohobot_session", token, **cookie_options)
    response.set_cookie("rohobot_role", user.role, **cookie_options)
    response.set_cookie("rohobot_access", access_state, **cookie_options)
    return {"success": True, "role": user.role, "destination": destination}


@router.get("/auth/me")
def get_me(user: CurrentUser, db: DbSession) -> dict:
    name = user.email
    if user.role == "candidate":
        profile = db.get(CandidateProfile, user.id)
        if profile:
            name = profile.full_name
    elif user.role == "employer":
        profile = db.get(EmployerProfile, user.id)
        if profile:
            name = profile.organization_name
    return {"id": str(user.id), "userId": str(user.id), "email": user.email, "role": user.role, "name": name}


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: DbSession) -> dict[str, bool]:
    token = request.cookies.get("rohobot_session")
    if token:
        session = db.get(UserSession, hash_token(token))
        if session:
            db.delete(session)
            db.commit()
    for name in ("rohobot_session", "rohobot_role", "rohobot_access"):
        response.delete_cookie(name, path="/")
    return {"success": True}


@router.get("/candidate/profile")
def get_candidate_profile(user: CandidateUser, db: DbSession) -> dict:
    profile = db.get(CandidateProfile, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile has not been created.")
    documents = db.scalars(
        select(CandidateDocument).where(CandidateDocument.owner_id == user.id)
    ).all()
    return {
        **profile.profile_data,
        "id": str(user.id),
        "fullName": profile.full_name,
        "gender": profile.profile_data.get("gender", ""),
        "dateOfBirth": profile.profile_data.get("dateOfBirth", ""),
        "phone": profile.phone or "",
        "email": user.email,
        "professionalCategory": profile.professional_category or "",
        "qualificationLevel": profile.qualification_level or "",
        "educationBackground": profile.profile_data.get("educationBackground", ""),
        "certifications": profile.profile_data.get("certifications", ""),
        "yearsOfExperience": profile.years_of_experience,
        "previousEmployment": profile.profile_data.get("previousEmployment", ""),
        "professionalSummary": profile.professional_summary or "",
        "skills": profile.skills,
        "currentLocation": profile.city or "",
        "preferredLocation": profile.profile_data.get("preferredLocation", ""),
        "employmentPreferences": profile.profile_data.get("employmentPreferences", ""),
        "availability": profile.availability,
        "preferredWorkArrangement": profile.profile_data.get("preferredWorkArrangement", "Full-time"),
        "consentGiven": profile.profile_data.get("consentGiven", False),
        "status": profile.status,
        "documents": [
            {
                "id": str(document.id),
                "category": document.category,
                "name": document.file_name,
                "contentType": document.content_type,
                "sizeBytes": document.size_bytes,
                "createdAt": document.created_at.isoformat(),
            }
            for document in documents
        ],
    }


@router.get("/candidate/documents")
def list_candidate_documents(user: CandidateUser, db: DbSession) -> list[dict]:
    documents = db.scalars(
        select(CandidateDocument)
        .where(CandidateDocument.owner_id == user.id)
        .order_by(CandidateDocument.created_at)
    ).all()
    return [
        {
            "id": str(document.id),
            "category": document.category,
            "name": document.file_name,
            "contentType": document.content_type,
            "sizeBytes": document.size_bytes,
            "createdAt": document.created_at.isoformat(),
        }
        for document in documents
    ]


@router.post("/candidate/documents", status_code=201)
async def upload_candidate_documents(
    categories: Annotated[list[str], Form()],
    files: Annotated[list[UploadFile], File()],
    user: CandidateUser,
    db: DbSession,
) -> dict[str, list[dict]]:
    allowed_categories = {
        "profilePhoto",
        "educationCertificates",
        "professionalLicenses",
        "nationalIdFront",
        "nationalIdBack",
        "experienceLetter",
    }
    if not files or len(files) != len(categories) or len(files) > 20:
        raise HTTPException(status_code=422, detail="Choose between 1 and 20 files and provide a category for each.")
    if not db.get(CandidateProfile, user.id):
        raise HTTPException(status_code=404, detail="Candidate profile has not been created.")

    saved_documents = []
    total_bytes = 0
    names_in_request = set()
    for category, uploaded_file in zip(categories, files):
        if category not in allowed_categories:
            raise HTTPException(status_code=422, detail="A document category is invalid.")
        content_type = uploaded_file.content_type or ""
        if content_type not in {"application/pdf", "image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=415, detail="Only PDF, JPEG, PNG, and WebP documents are supported.")
        if category == "profilePhoto" and not content_type.startswith("image/"):
            raise HTTPException(status_code=415, detail="Profile photos must be an image.")

        filename = PurePosixPath((uploaded_file.filename or "").replace("\\", "/")).name.strip()
        if not filename or len(filename) > 255:
            raise HTTPException(status_code=422, detail="A file name is missing or too long.")
        name_key = (category, filename.casefold())
        if name_key in names_in_request:
            raise HTTPException(status_code=422, detail="A file name is duplicated within the same document category.")
        names_in_request.add(name_key)
        content = await uploaded_file.read(10 * 1024 * 1024 + 1)
        if not content:
            raise HTTPException(status_code=422, detail=f"{filename} is empty.")
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"{filename} exceeds the 10 MB per-file limit.")
        total_bytes += len(content)
        if total_bytes > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="The combined upload exceeds the 25 MB request limit.")

        document = db.scalar(
            select(CandidateDocument).where(
                CandidateDocument.owner_id == user.id,
                CandidateDocument.category == category,
                CandidateDocument.file_name == filename,
            )
        )
        if document:
            document.content_type = content_type
            document.size_bytes = len(content)
            document.content = content
        else:
            document = CandidateDocument(
                owner_id=user.id,
                category=category,
                file_name=filename,
                content_type=content_type,
                size_bytes=len(content),
                content=content,
            )
            db.add(document)
        saved_documents.append(document)
        await uploaded_file.close()

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="A document with the same name was uploaded concurrently.") from error
    for document in saved_documents:
        db.refresh(document)
    return {
        "documents": [
            {
                "id": str(document.id),
                "category": document.category,
                "name": document.file_name,
                "contentType": document.content_type,
                "sizeBytes": document.size_bytes,
                "createdAt": document.created_at.isoformat(),
            }
            for document in saved_documents
        ]
    }


@router.get("/candidate/documents/{document_id}")
def download_candidate_document(document_id: UUID, user: CandidateUser, db: DbSession) -> Response:
    document = db.get(CandidateDocument, document_id)
    if not document or document.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(
        content=document.content,
        media_type=document.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(document.file_name)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch("/candidate/profile/availability")
def update_candidate_availability(data: dict, user: CandidateUser, db: DbSession) -> dict[str, bool]:
    availability = data.get("availability")
    if availability not in {"Immediate", "1 Week", "1 Month", "Not Available"}:
        raise HTTPException(status_code=422, detail="Choose a valid availability status.")
    profile = db.get(CandidateProfile, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile has not been created.")
    profile.availability = availability
    db.commit()
    return {"success": True}


@router.get("/employers/profile")
def get_employer_profile(user: EmployerUser, db: DbSession) -> dict:
    profile = db.get(EmployerProfile, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Employer profile has not been created.")
    extra = profile.profile_data
    return {
        **extra,
        "id": str(user.id),
        "organizationName": profile.organization_name,
        "organizationType": profile.organization_type or "",
        "city": profile.city or "",
        "website": profile.website or "",
        "hrEmail": extra.get("hrEmail", user.email),
        "hrPhone": extra.get("hrPhone", profile.phone or ""),
        "address": extra.get("address", profile.city or ""),
        "status": profile.status,
        "profileComplete": bool(profile.profile_data.get("tinNumber")),
        "packageName": profile.profile_data.get("packageName"),
        "paymentStatus": profile.profile_data.get("paymentStatus"),
        "reviewNote": profile.profile_data.get("reviewNote"),
    }


@router.post("/employers/package")
def select_employer_package(data: dict, user: EmployerUser, db: DbSession) -> dict[str, bool]:
    package_name = data.get("packageName")
    if package_name not in {"Basic", "Silver", "Gold"}:
        raise HTTPException(status_code=422, detail="Choose a valid package.")
    profile = db.get(EmployerProfile, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Employer profile has not been created.")
    profile.profile_data = {**profile.profile_data, "packageName": package_name}
    db.commit()
    return {"success": True}


@router.put("/employers/profile")
def save_employer_profile(data: dict, user: EmployerUser, db: DbSession) -> dict[str, bool]:
    name = data.get("organizationName")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=422, detail="Organization name is required.")
    profile = db.get(EmployerProfile, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Employer profile has not been created.")
    profile.organization_name = name.strip()
    profile.organization_type = str(data.get("organizationType") or "")[:80]
    profile.city = str(data.get("city") or data.get("address") or "")[:120]
    profile.website = str(data.get("website") or "")[:255]
    profile.phone = str(data.get("hrPhone") or profile.phone or "")[:40]
    profile.profile_data = {**profile.profile_data, **data}
    profile.status = "Pending Admin Review"
    db.commit()
    return {"success": True}


@router.post("/employers/subscription", status_code=201)
def submit_employer_subscription(data: dict, user: EmployerUser, db: DbSession) -> dict:
    profile = db.get(EmployerProfile, user.id)
    if not profile or profile.status == "Pending OTP":
        raise HTTPException(status_code=409, detail="Verify your email and complete your organization profile first.")
    tier = data.get("subscriptionTier")
    if tier not in {"Basic", "Silver", "Gold", "Premium"}:
        raise HTTPException(status_code=422, detail="Choose a valid subscription package.")
    profile.profile_data = {
        **profile.profile_data,
        **data,
        "subscriptionTier": tier,
        "paymentSubmitted": True,
    }
    profile.status = "Pending Admin Review"
    transaction = ApplicationRecord(
        resource="transactions",
        owner_id=user.id,
        payload={
            "referenceNumber": str(data.get("transactionReference") or f"LOCAL-{uuid4().hex[:12]}"),
            "employerName": profile.organization_name,
            "packageTier": tier,
            "amount": int(data.get("amount") or 0),
            "date": datetime.now(timezone.utc).isoformat(),
            "status": "Pending",
            "paymentMethod": data.get("paymentMethod"),
            "localOnly": True,
        },
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return {"success": True, "transactionId": str(transaction.id)}


@router.get("/admin/employers")
def list_employers(user: AdminUser, db: DbSession) -> list[dict]:
    profiles = db.scalars(select(EmployerProfile).order_by(EmployerProfile.organization_name)).all()
    result = []
    for profile in profiles:
        account = db.get(User, profile.user_id)
        if not account:
            continue
        result.append(
            {
                **profile.profile_data,
                "id": str(account.id),
                "organizationName": profile.organization_name,
                "organizationType": profile.organization_type or "",
                "status": profile.status,
                "orgEmail": account.email,
                "orgPhone": profile.phone or "",
                "paymentSubmitted": bool(profile.profile_data.get("paymentSubmitted", False)),
            }
        )
    return result


@router.get("/admin/invitations")
def list_candidate_invitations(user: AdminUser, db: DbSession) -> dict:
    now = datetime.now(timezone.utc)
    invitations = db.scalars(
        select(CandidateInvitation).order_by(CandidateInvitation.created_at.desc())
    ).all()
    return {
        "invitations": [
            {
                "id": str(invitation.id),
                "expiresAt": invitation.expires_at.isoformat(),
                "status": (
                    "Used"
                    if invitation.used_at
                    else "Revoked"
                    if invitation.revoked_at
                    else "Expired"
                    if invitation.expires_at <= now
                    else "Pending"
                ),
            }
            for invitation in invitations
        ]
    }


@router.post("/admin/invitations", status_code=201)
def create_candidate_invitation(user: AdminUser, db: DbSession) -> dict:
    token = new_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
    invitation = CandidateInvitation(
        token_hash=hash_token(token),
        created_by=user.id,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return {
        "invitation": {
            "id": str(invitation.id),
            "expiresAt": invitation.expires_at.isoformat(),
            "status": "Pending",
        },
        "token": token,
    }


@router.delete("/admin/invitations/{invitation_id}")
def revoke_candidate_invitation(invitation_id: UUID, user: AdminUser, db: DbSession) -> dict[str, bool]:
    invitation = db.get(CandidateInvitation, invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if invitation.used_at or invitation.revoked_at or invitation.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Only pending invitations can be revoked.")
    invitation.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True}


@router.get("/admin/email-outbox")
def get_email_outbox(user: AdminUser, db: DbSession) -> list[dict]:
    emails = db.scalars(
        select(EmailOutbox).order_by(EmailOutbox.created_at.desc())
    ).all()
    return [
        {
            "id": str(email.id),
            "to": email.recipient,
            "subject": email.subject,
            "body": email.body,
            "link": email.link,
            "type": email.category,
            "sentAt": (email.sent_at or email.created_at).isoformat(),
            "opened": email.opened,
            "deliveryStatus": email.delivery_status,
            "attemptCount": email.attempt_count,
            "lastError": email.last_error,
        }
        for email in emails
    ]


@router.post("/admin/email-outbox", status_code=201)
def create_email(
    data: EmailCreate, user: AdminUser, db: DbSession, background_tasks: BackgroundTasks
) -> dict:
    email = EmailOutbox(
        recipient=str(data.to),
        subject=data.subject,
        body=data.body,
        link=data.link,
        category=data.type,
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    background_tasks.add_task(deliver_email, email.id)
    return {
        "id": str(email.id),
        "to": email.recipient,
        "subject": email.subject,
        "body": email.body,
        "link": email.link,
        "type": email.category,
        "sentAt": (email.sent_at or email.created_at).isoformat(),
        "opened": email.opened,
        "deliveryStatus": email.delivery_status,
        "attemptCount": email.attempt_count,
        "lastError": email.last_error,
    }


@router.patch("/admin/email-outbox/{email_id}")
def mark_email_opened(email_id: UUID, user: AdminUser, db: DbSession) -> dict[str, bool]:
    email = db.get(EmailOutbox, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")
    email.opened = True
    db.commit()
    return {"success": True}


@router.delete("/admin/email-outbox", status_code=204)
def clear_email_outbox(user: AdminUser, db: DbSession) -> Response:
    db.query(EmailOutbox).delete()
    db.commit()
    return Response(status_code=204)


@router.patch("/admin/employers/{employer_id}")
def review_employer(
    employer_id: UUID,
    data: dict,
    user: AdminUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> dict[str, bool]:
    profile = db.get(EmployerProfile, employer_id)
    account = db.get(User, employer_id)
    status = data.get("status")
    if not profile or not account:
        raise HTTPException(status_code=404, detail="Employer account not found.")
    if status not in {"Active", "Rejected"}:
        raise HTTPException(status_code=422, detail="Choose Active or Rejected.")
    profile.status = status
    profile.profile_data = {**profile.profile_data, "rejectionReason": data.get("reason")}
    account.is_active = status == "Active"
    outbox_email = EmailOutbox(
        recipient=account.email,
        subject="Your Rohobot employer profile was reviewed",
        body=str(data.get("reason") or f"Your organization status is now {status}."),
        category="profile_review",
    )
    db.add(outbox_email)
    db.commit()
    background_tasks.add_task(deliver_email, outbox_email.id)
    return {"success": True}


@router.get("/admin/verifications")
def list_verifications(user: AdminUser, db: DbSession) -> list[dict]:
    candidates = db.scalars(select(CandidateProfile)).all()
    employers = db.scalars(select(EmployerProfile)).all()
    rows = []
    for profile in candidates:
        documents = db.scalars(
            select(CandidateDocument).where(CandidateDocument.owner_id == profile.user_id)
        ).all()
        rows.append(
            {
                "id": f"candidate:{profile.user_id}",
                "name": profile.full_name,
                "type": "Candidate",
                "roleOrCategory": profile.professional_category or "",
                "submittedDate": profile.user_id and (
                    db.get(User, profile.user_id).created_at.date().isoformat()
                    if db.get(User, profile.user_id)
                    else ""
                ),
                "documents": [
                    {
                        "id": str(document.id),
                        "category": document.category,
                        "name": document.file_name,
                        "contentType": document.content_type,
                        "sizeBytes": document.size_bytes,
                        "createdAt": document.created_at.isoformat(),
                    }
                    for document in documents
                ],
                "status": {
                    "Verified": "Approved",
                    "Rejected": "Rejected",
                    "Pending OTP": "Unverified",
                }.get(profile.status, "Pending"),
            }
        )
    for profile in employers:
        account = db.get(User, profile.user_id)
        rows.append(
            {
                "id": f"employer:{profile.user_id}",
                "name": profile.organization_name,
                "type": "Employer",
                "roleOrCategory": profile.organization_type or "",
                "submittedDate": account.created_at.date().isoformat() if account else "",
                "status": {
                    "Active": "Approved",
                    "Rejected": "Rejected",
                    "Pending OTP": "Unverified",
                }.get(profile.status, "Pending"),
            }
        )
    return rows


@router.get("/admin/candidates/{candidate_id}/documents")
def list_candidate_documents_for_admin(candidate_id: UUID, user: AdminUser, db: DbSession) -> list[dict]:
    if not db.get(CandidateProfile, candidate_id):
        raise HTTPException(status_code=404, detail="Candidate profile not found.")
    documents = db.scalars(
        select(CandidateDocument)
        .where(CandidateDocument.owner_id == candidate_id)
        .order_by(CandidateDocument.created_at)
    ).all()
    return [
        {
            "id": str(document.id),
            "category": document.category,
            "name": document.file_name,
            "contentType": document.content_type,
            "sizeBytes": document.size_bytes,
            "createdAt": document.created_at.isoformat(),
        }
        for document in documents
    ]


@router.get("/admin/candidates/{candidate_id}/documents/{document_id}")
def download_candidate_document_for_admin(
    candidate_id: UUID,
    document_id: UUID,
    user: AdminUser,
    db: DbSession,
) -> Response:
    document = db.get(CandidateDocument, document_id)
    if not document or document.owner_id != candidate_id:
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(
        content=document.content,
        media_type=document.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(document.file_name)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/admin/analytics")
def get_admin_analytics(
    user: AdminUser,
    db: DbSession,
    category: str = "",
    location: str = "",
) -> dict:
    candidates = db.scalars(select(CandidateProfile)).all()
    employers = db.scalars(select(EmployerProfile)).all()
    transactions = db.scalars(
        select(ApplicationRecord).where(ApplicationRecord.resource == "transactions")
    ).all()
    interviews = db.scalars(
        select(ApplicationRecord).where(ApplicationRecord.resource == "interviews")
    ).all()
    placements = db.scalars(
        select(ApplicationRecord).where(ApplicationRecord.resource == "placements")
    ).all()
    declines = db.scalars(
        select(ApplicationRecord).where(ApplicationRecord.resource == "decline-records")
    ).all()
    scoped_candidates = [
        profile
        for profile in candidates
        if (not category or profile.professional_category == category)
        and (not location or profile.city == location)
    ]
    successful_revenue = sum(
        int(record.payload.get("amount") or 0)
        for record in transactions
        if record.payload.get("status") == "Successful"
    )
    candidate_categories: dict[str, int] = {}
    candidate_locations: dict[str, int] = {}
    for profile in scoped_candidates:
        candidate_categories[profile.professional_category or "Unspecified"] = (
            candidate_categories.get(profile.professional_category or "Unspecified", 0) + 1
        )
        candidate_locations[profile.city or "Unspecified"] = (
            candidate_locations.get(profile.city or "Unspecified", 0) + 1
        )
    return {
        "totalCandidates": len(scoped_candidates),
        "verifiedCandidates": sum(1 for profile in scoped_candidates if profile.verified),
        "pendingVerifications": sum(1 for profile in scoped_candidates if profile.status == "Pending Review"),
        "unavailableCandidates": sum(
            1 for profile in scoped_candidates if profile.availability == "Not Available"
        ),
        "genderSplit": {"male": 0, "female": 0},
        "categorySplit": [{"name": key, "value": value} for key, value in candidate_categories.items()],
        "locationSplit": [{"name": key, "value": value} for key, value in candidate_locations.items()],
        "totalEmployers": len(employers),
        "verifiedEmployers": sum(1 for profile in employers if profile.status == "Active"),
        "activeSubscriptions": {
            tier.lower(): sum(
                1
                for profile in employers
                if profile.status == "Active" and profile.profile_data.get("subscriptionTier") == tier
            )
            for tier in ("Gold", "Silver", "Basic")
        },
        "totalRevenue": successful_revenue,
        "interviewsSent": len(interviews),
        "interviewsAccepted": sum(1 for record in interviews if record.payload.get("status") == "Accepted"),
        "interviewsDeclined": sum(1 for record in interviews if record.payload.get("status") == "Declined"),
        "interviewsCompleted": sum(1 for record in interviews if record.payload.get("status") == "Completed"),
        "placementsCommenced": sum(
            1 for record in placements if record.payload.get("stage") == "Commenced Employment"
        ),
        "flaggedCandidates": sum(
            1 for record in declines if record.payload.get("flagStatus") == "Flagged"
        ),
    }


@router.patch("/admin/verifications/{verification_id}")
def update_verification(
    verification_id: str,
    data: dict,
    user: AdminUser,
    db: DbSession,
) -> dict[str, bool]:
    status = data.get("status")
    if status not in {"Approved", "Rejected"}:
        raise HTTPException(status_code=422, detail="Choose Approved or Rejected.")
    try:
        entity_type, entity_id = verification_id.split(":", 1)
        entity_uuid = UUID(entity_id)
    except (ValueError, AttributeError) as error:
        raise HTTPException(status_code=422, detail="Verification ID is invalid.") from error

    if entity_type == "candidate":
        profile = db.get(CandidateProfile, entity_uuid)
        if not profile:
            raise HTTPException(status_code=404, detail="Candidate profile not found.")
        profile.status = "Verified" if status == "Approved" else "Rejected"
        profile.verified = status == "Approved"
    elif entity_type == "employer":
        profile = db.get(EmployerProfile, entity_uuid)
        account = db.get(User, entity_uuid)
        if not profile or not account:
            raise HTTPException(status_code=404, detail="Employer profile not found.")
        profile.status = "Active" if status == "Approved" else "Rejected"
        account.is_active = status == "Approved"
    else:
        raise HTTPException(status_code=422, detail="Verification type is invalid.")
    db.commit()
    return {"success": True}


@router.put("/candidate/profile")
def save_candidate_profile(data: dict, user: CandidateUser, db: DbSession) -> dict[str, bool]:
    full_name = data.get("fullName")
    if not isinstance(full_name, str) or not full_name.strip():
        raise HTTPException(status_code=422, detail="Full name is required.")
    profile = db.get(CandidateProfile, user.id)
    if not profile:
        profile = CandidateProfile(user_id=user.id, full_name=full_name.strip())
        db.add(profile)
    profile.full_name = full_name.strip()
    profile.phone = str(data.get("phone") or "")[:40]
    profile.professional_category = str(data.get("professionalCategory") or "")[:120]
    profile.qualification_level = str(data.get("qualificationLevel") or "")[:120]
    profile.years_of_experience = max(0, int(data.get("yearsOfExperience") or 0))
    profile.professional_summary = str(data.get("professionalSummary") or "")
    profile.skills = data.get("skills") if isinstance(data.get("skills"), list) else []
    profile.city = str(data.get("currentLocation") or "")[:120]
    profile.availability = str(data.get("availability") or "Not Available")[:40]
    profile.profile_data = {
        key: value
        for key, value in data.items()
        if key not in {
            "id", "email", "fullName", "phone", "professionalCategory",
            "qualificationLevel", "yearsOfExperience", "professionalSummary",
            "skills", "currentLocation", "availability", "status",
        }
    }
    profile.status = "Pending Review"
    db.commit()
    return {"success": True}


@router.get("/employers/search-candidates")
def search_candidates(
    user: EmployerUser,
    db: DbSession,
    query: str = "",
    category: str = "",
    qualification: str = "",
    location: str = "",
    min_experience: int = Query(default=0, ge=0),
    availability: str = "",
    work_arrangement: str = "",
) -> list[dict]:
    employer = db.get(EmployerProfile, user.id)
    if not employer or employer.status != "Active":
        raise HTTPException(status_code=403, detail="An approved employer account is required to search candidates.")
    profiles = db.scalars(
        select(CandidateProfile)
        .join(User, CandidateProfile.user_id == User.id)
        .where(
            CandidateProfile.verified.is_(True),
            CandidateProfile.availability != "Not Available",
            User.is_active.is_(True),
        )
    ).all()
    saved_records = db.scalars(
        select(ApplicationRecord).where(
            ApplicationRecord.resource == "saved-candidates",
            ApplicationRecord.owner_id == user.id,
        )
    ).all()
    saved_ids = {record.payload.get("candidateId") for record in saved_records}
    needle = query.casefold().strip()
    results = []
    for profile in profiles:
        owner = db.get(User, profile.user_id)
        extra = profile.profile_data
        name = profile.full_name
        role = profile.professional_category or ""
        skills = profile.skills
        city = profile.city or ""
        arrangement = extra.get("preferredWorkArrangement", "")
        haystack = " ".join([name, role, profile.qualification_level or "", *skills]).casefold()
        if (
            (needle and needle not in haystack)
            or (category and role != category)
            or (qualification and qualification.casefold() not in (profile.qualification_level or "").casefold())
            or (location and city != location)
            or profile.years_of_experience < min_experience
            or (availability and profile.availability != availability)
            or (work_arrangement and arrangement != work_arrangement)
        ):
            continue
        score = 50 + profile.years_of_experience
        reasons = []
        if profile.availability == "Immediate":
            score += 20
            reasons.append({"label": "Available Immediately", "type": "positive"})
        if profile.years_of_experience >= 5:
            score += 15
            reasons.append({"label": "5+ Years Experience", "type": "positive"})
        if location and city == location:
            score += 15
            reasons.append({"label": "Located in Preferred Area", "type": "positive"})
        if qualification and qualification.casefold() in (profile.qualification_level or "").casefold():
            reasons.append({"label": f"{profile.qualification_level} qualification", "type": "positive"})
        if work_arrangement and arrangement == work_arrangement:
            reasons.append({"label": f"{arrangement} preference", "type": "positive"})
        results.append(
            {
                "id": str(profile.user_id),
                "name": name,
                "role": role,
                "qualification": profile.qualification_level or "",
                "experienceYears": profile.years_of_experience,
                "location": city,
                "professionalSummary": profile.professional_summary or "",
                "skills": skills,
                "availability": profile.availability,
                "workArrangement": arrangement,
                "isVerified": profile.verified,
                "isActive": bool(owner and owner.is_active),
                "isSaved": str(profile.user_id) in saved_ids,
                "matchScore": min(score, 100),
                "matchReasons": reasons,
            }
        )
    results.sort(key=lambda result: result["matchScore"], reverse=True)
    filters_used = [
        value
        for value in (category, qualification, location, f"{min_experience}+ yrs" if min_experience else "", availability, work_arrangement)
        if value
    ]
    db.add(
        ApplicationRecord(
            resource="audit-logs",
            owner_id=user.id,
            payload={
                "employerName": employer.organization_name if employer else user.email,
                "searchQuery": query,
                "filtersUsed": filters_used,
                "resultsCount": len(results),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    )
    db.commit()
    return results


@router.post("/employers/saved-candidates/{candidate_id}")
def toggle_saved_candidate(candidate_id: UUID, user: EmployerUser, db: DbSession) -> dict[str, bool]:
    record = db.scalar(
        select(ApplicationRecord).where(
            ApplicationRecord.resource == "saved-candidates",
            ApplicationRecord.owner_id == user.id,
            ApplicationRecord.payload["candidateId"].as_string() == str(candidate_id),
        )
    )
    if record:
        db.delete(record)
        saved = False
    else:
        db.add(
            ApplicationRecord(
                id=uuid4(),
                resource="saved-candidates",
                owner_id=user.id,
                payload={"candidateId": str(candidate_id)},
            )
        )
        saved = True
    db.commit()
    return {"saved": saved}


@router.get("/jobs", response_model=JobList)
def list_jobs(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JobList:
    jobs = db.scalars(
        select(Job)
        .where(Job.status == "published")
        .order_by(Job.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return JobList(items=jobs, limit=limit, offset=offset)


@router.post("/jobs", status_code=201)
def create_job(data: dict, user: EmployerUser, db: DbSession) -> dict:
    employer = db.get(EmployerProfile, user.id)
    if not employer or employer.status != "Active":
        raise HTTPException(status_code=403, detail="An approved employer profile is required to post jobs.")
    required = ("title", "description", "location", "employmentType")
    if any(not isinstance(data.get(key), str) or not data[key].strip() for key in required):
        raise HTTPException(status_code=422, detail="Title, description, location, and employment type are required.")
    job = Job(
        employer_id=user.id,
        title=data["title"].strip(),
        description=data["description"].strip(),
        location=data["location"].strip(),
        employment_type=data["employmentType"].strip(),
        status="published",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"id": str(job.id), "employerId": str(job.employer_id), "title": job.title}


@router.post("/jobs/{job_id}/applications", status_code=201)
def apply_for_job(job_id: UUID, data: dict, user: CandidateUser, db: DbSession) -> dict:
    job = db.get(Job, job_id)
    if not job or job.status != "published":
        raise HTTPException(status_code=404, detail="Published job not found.")
    if not db.get(CandidateProfile, user.id):
        raise HTTPException(status_code=409, detail="Complete your candidate profile before applying.")
    application = JobApplication(job_id=job_id, candidate_id=user.id, cover_letter=data.get("coverLetter"))
    db.add(application)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already applied for this job.") from error
    return {"success": True, "applicationId": str(application.id)}


@router.get("/records/{resource}")
def list_records(resource: str, user: CurrentUser, db: DbSession) -> list[dict]:
    if resource not in RESOURCE_NAMES:
        raise HTTPException(status_code=404, detail="Unknown resource.")
    statement = select(ApplicationRecord).where(ApplicationRecord.resource == resource)
    if user.role != "admin" and resource != "courses":
        owner_filter = ApplicationRecord.owner_id == user.id
        if resource in {"interviews", "placements"} and user.role == "candidate":
            owner_filter = or_(
                owner_filter,
                ApplicationRecord.payload["candidateId"].as_string() == str(user.id),
            )
        statement = statement.where(owner_filter)
    return [
        {"id": str(record.id), **record.payload}
        for record in db.scalars(statement.order_by(ApplicationRecord.created_at.desc())).all()
    ]


@router.post("/records/{resource}", status_code=201)
def create_record(resource: str, data: RecordCreate, user: CurrentUser, db: DbSession) -> dict:
    if resource not in RESOURCE_NAMES:
        raise HTTPException(status_code=404, detail="Unknown resource.")
    if resource in {"decline-records", "reviews", "verifications", "trainer-settings"} and user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    if resource in {"feedback", "interviews", "placements", "saved-candidates", "subscriptions", "transactions"} and user.role != "employer":
        raise HTTPException(status_code=403, detail="Employer access is required.")
    if resource in {"career-enrollments", "certificates"} and user.role != "candidate":
        raise HTTPException(status_code=403, detail="Candidate access is required.")
    if resource == "courses" and user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    if resource == "email-outbox" and user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    if resource == "transactions" and user.role != "admin":
        if data.payload.get("status", "Pending") != "Pending":
            raise HTTPException(status_code=403, detail="Only verified gateway payments or administrators can change payment status.")
        data.payload["status"] = "Pending"
    if resource in {"audit-logs"} and user.role not in {"employer", "admin"}:
        raise HTTPException(status_code=403, detail="Employer or administrator access is required.")
    if resource == "interviews":
        candidate_id = data.payload.get("candidateId")
        try:
            candidate_uuid = UUID(str(candidate_id))
        except ValueError as error:
            raise HTTPException(status_code=422, detail="A valid candidate ID is required.") from error
        if not db.get(CandidateProfile, candidate_uuid):
            raise HTTPException(status_code=404, detail="Candidate profile not found.")
        data.payload["candidateId"] = str(candidate_uuid)
    if resource == "notifications" and data.payload.get("targetRole") != user.role:
        raise HTTPException(status_code=403, detail="Notifications can only be created for your own account.")
    record = ApplicationRecord(resource=resource, owner_id=user.id, payload=data.payload)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": str(record.id), **record.payload}


@router.patch("/records/{resource}/{record_id}")
def update_record(resource: str, record_id: UUID, data: RecordUpdate, user: CurrentUser, db: DbSession) -> dict:
    if resource not in RESOURCE_NAMES:
        raise HTTPException(status_code=404, detail="Unknown resource.")
    if resource == "transactions" and user.role != "admin":
        raise HTTPException(status_code=403, detail="Payment transactions can only be updated by administrators or the payment provider.")
    statement = select(ApplicationRecord).where(
        ApplicationRecord.id == record_id,
        ApplicationRecord.resource == resource,
    )
    if user.role != "admin":
        access_filter = ApplicationRecord.owner_id == user.id
        if resource in {"interviews", "placements"} and user.role == "candidate":
            access_filter = or_(
                access_filter,
                ApplicationRecord.payload["candidateId"].as_string() == str(user.id),
            )
        statement = statement.where(access_filter)
    record = db.scalar(statement)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
    if resource == "interviews" and user.role == "candidate":
        if not set(data.payload).issubset({"status", "declineReason", "rescheduleReason", "proposedNewDate"}):
            raise HTTPException(status_code=403, detail="Candidates may only respond to their interview.")
        if data.payload.get("status") not in {"Accepted", "Declined", "Rescheduling Requested"}:
            raise HTTPException(status_code=422, detail="Interview status is invalid.")
    record.payload = {**record.payload, **data.payload}
    db.commit()
    return {"id": str(record.id), **record.payload}


@router.delete("/records/{resource}/{record_id}", status_code=204)
def delete_record(resource: str, record_id: UUID, user: CurrentUser, db: DbSession) -> Response:
    if resource not in RESOURCE_NAMES:
        raise HTTPException(status_code=404, detail="Unknown resource.")
    statement = select(ApplicationRecord).where(
        ApplicationRecord.id == record_id,
        ApplicationRecord.resource == resource,
    )
    if user.role != "admin":
        statement = statement.where(ApplicationRecord.owner_id == user.id)
    record = db.scalar(statement)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
    db.delete(record)
    db.commit()
    return Response(status_code=204)
