import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from uuid import UUID

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import EmailOutbox


def deliver_email(email_id: UUID) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        return

    with SessionLocal() as db:
        email = db.get(EmailOutbox, email_id)
        if not email or email.delivery_status == "sent":
            return

        email.attempt_count += 1
        try:
            message = EmailMessage()
            message["From"] = settings.smtp_from_email
            message["To"] = email.recipient
            message["Subject"] = email.subject
            message.set_content(email.body)

            if settings.smtp_use_ssl:
                with smtplib.SMTP_SSL(
                    settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
                ) as client:
                    if settings.smtp_username:
                        client.login(settings.smtp_username, settings.smtp_password)
                    client.send_message(message)
            else:
                with smtplib.SMTP(
                    settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
                ) as client:
                    if settings.smtp_use_tls:
                        client.starttls()
                    if settings.smtp_username:
                        client.login(settings.smtp_username, settings.smtp_password)
                    client.send_message(message)
        except (OSError, smtplib.SMTPException, ValueError) as error:
            email.delivery_status = "failed"
            email.last_error = str(error)[:1000]
            db.commit()
            return

        email.delivery_status = "sent"
        email.last_error = None
        email.sent_at = datetime.now(timezone.utc)
        db.commit()
