import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.core.config import settings
from app.db.session import get_db
from app.models import ApplicationRecord, EmployerProfile, User

router = APIRouter(prefix="/payments", tags=["payments"])
DbSession = Annotated[Session, Depends(get_db)]
EmployerUser = Annotated[User, Depends(require_role("employer"))]

PACKAGE_PRICES = {"Basic": Decimal("500"), "Silver": Decimal("1500"), "Gold": Decimal("3000")}


def _configured() -> None:
    if settings.payment_provider.lower() != "chapa" or not settings.chapa_secret_key:
        raise HTTPException(status_code=503, detail="Online payment is not configured.")


def _gateway_request(method: str, path: str, **kwargs) -> dict:
    try:
        response = httpx.request(
            method,
            f"{settings.chapa_api_url.rstrip('/')}/{path.lstrip('/')}",
            headers={"Authorization": f"Bearer {settings.chapa_secret_key}"},
            timeout=settings.payment_timeout_seconds,
            **kwargs,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Payment provider request failed.") from error
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="Payment provider returned an invalid response.")
    return payload


def _transaction(db: Session, reference: str) -> ApplicationRecord | None:
    return db.scalar(
        select(ApplicationRecord).where(
            ApplicationRecord.resource == "transactions",
            ApplicationRecord.payload["referenceNumber"].as_string() == reference,
        )
    )


def _verify_and_update(db: Session, record: ApplicationRecord) -> str:
    payload = record.payload
    result = _gateway_request("GET", f"transaction/verify/{payload['referenceNumber']}")
    if result.get("status") != "success":
        raise HTTPException(status_code=502, detail="Payment provider could not verify this transaction.")
    data = result.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Payment provider returned an invalid verification response.")

    reference = data.get("tx_ref")
    currency = str(data.get("currency") or "").upper()
    try:
        amount = Decimal(str(data.get("amount")))
        expected_amount = Decimal(str(payload["amount"]))
    except (InvalidOperation, KeyError, TypeError) as error:
        raise HTTPException(status_code=502, detail="Payment provider returned invalid transaction details.") from error

    verified = (
        str(reference) == str(payload["referenceNumber"])
        and currency == str(payload.get("currency", "ETB")).upper()
        and amount == expected_amount
    )
    provider_status = str(data.get("status") or "").lower()
    if not verified:
        raise HTTPException(status_code=409, detail="Payment verification details do not match this transaction.")

    if provider_status == "success":
        if payload.get("status") != "Successful":
            payload = {**payload, "status": "Successful", "verifiedBy": "chapa"}
            record.payload = payload
            profile = db.get(EmployerProfile, record.owner_id)
            if profile:
                profile.status = "Active"
                profile.profile_data = {
                    **profile.profile_data,
                    "subscriptionTier": payload["packageTier"],
                    "paymentSubmitted": True,
                }
    elif provider_status in {"failed", "cancelled"} and payload.get("status") != "Successful":
        record.payload = {**payload, "status": "Failed"}
    db.commit()
    return str(record.payload.get("status", "Pending"))


@router.post("/chapa/checkout")
def initiate_checkout(
    data: dict,
    db: DbSession,
    user: EmployerUser,
) -> dict:
    _configured()
    profile = db.get(EmployerProfile, user.id)
    if not profile or profile.status == "Pending OTP":
        raise HTTPException(status_code=409, detail="Verify your email and complete your organization profile first.")

    tier = data.get("packageTier")
    if tier not in PACKAGE_PRICES:
        raise HTTPException(status_code=422, detail="Choose a valid subscription package.")
    amount = PACKAGE_PRICES[tier]
    reference = f"RHB-{uuid4().hex}"
    record = ApplicationRecord(
        resource="transactions",
        owner_id=user.id,
        payload={
            "referenceNumber": reference,
            "employerName": profile.organization_name,
            "packageTier": tier,
            "amount": int(amount),
            "currency": "ETB",
            "date": datetime.now(timezone.utc).isoformat(),
            "status": "Pending",
            "paymentMethod": "Chapa",
            "provider": "chapa",
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    names = (profile.organization_name or "Rohobot Employer").split()
    callback = f"{settings.public_api_url.rstrip('/')}/api/payments/chapa/callback"
    return_url = (
        f"{settings.frontend_base_url.rstrip('/')}/employer/subscription?"
        + urlencode({"transactionId": str(record.id), "payment": "return"})
    )
    result = _gateway_request(
        "POST",
        "transaction/initialize",
        json={
            "amount": str(amount),
            "currency": "ETB",
            "email": user.email,
            "first_name": names[0],
            "last_name": " ".join(names[1:]) or names[0],
            "tx_ref": reference,
            "callback_url": callback,
            "return_url": return_url,
            "customization": {"title": "Rohobot Subscription", "description": f"{tier} subscription"},
        },
    )
    response_data = result.get("data")
    checkout_url = response_data.get("checkout_url") if isinstance(response_data, dict) else None
    if result.get("status") != "success" or not isinstance(checkout_url, str) or not checkout_url.startswith("https://"):
        raise HTTPException(status_code=502, detail="Payment provider did not return a valid checkout URL.")

    record.payload = {**record.payload, "checkoutUrl": checkout_url}
    db.commit()
    return {"checkoutUrl": checkout_url, "transactionId": str(record.id)}


@router.get("/transactions/{transaction_id}")
def get_payment_status(
    transaction_id: UUID,
    db: DbSession,
    user: EmployerUser,
) -> dict:
    record = db.scalar(
        select(ApplicationRecord).where(
            ApplicationRecord.id == transaction_id,
            ApplicationRecord.resource == "transactions",
            ApplicationRecord.owner_id == user.id,
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    status = str(record.payload.get("status", "Pending"))
    if status == "Pending" and record.payload.get("provider") == "chapa":
        _configured()
        status = _verify_and_update(db, record)
    return {"transactionId": str(record.id), "status": status}


def _callback_redirect(transaction_id: str | None, status: str) -> RedirectResponse:
    query = urlencode({"payment": status.lower(), **({"transactionId": transaction_id} if transaction_id else {})})
    return RedirectResponse(
        f"{settings.frontend_base_url.rstrip('/')}/employer/subscription?{query}",
        status_code=303,
    )


@router.get("/chapa/callback")
def chapa_callback(
    db: DbSession,
    tx_ref: str | None = Query(default=None),
    trx_ref: str | None = Query(default=None),
) -> RedirectResponse:
    reference = tx_ref or trx_ref
    record = _transaction(db, reference) if reference else None
    if not record:
        return _callback_redirect(None, "failed")
    try:
        status = _verify_and_update(db, record)
    except HTTPException:
        status = "Pending"
    return _callback_redirect(str(record.id), status)


@router.post("/chapa/webhook")
async def chapa_webhook(
    request: Request,
    db: DbSession,
    chapa_signature: str | None = Header(default=None, alias="chapa-signature"),
    x_chapa_signature: str | None = Header(default=None, alias="x-chapa-signature"),
) -> dict:
    if not settings.chapa_webhook_secret:
        raise HTTPException(status_code=503, detail="Payment webhook verification is not configured.")
    body = await request.body()
    supplied = (chapa_signature or x_chapa_signature or "").removeprefix("sha256=")
    expected = hmac.new(settings.chapa_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid payment webhook signature.")
    try:
        event = await request.json()
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from error
    reference = event.get("tx_ref") if isinstance(event, dict) else None
    if not isinstance(reference, str) or not reference:
        raise HTTPException(status_code=400, detail="Webhook transaction reference is missing.")
    record = _transaction(db, reference)
    if not record:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    _configured()
    _verify_and_update(db, record)
    return {"received": True}
