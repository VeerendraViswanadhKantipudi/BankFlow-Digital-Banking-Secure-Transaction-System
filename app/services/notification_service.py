"""
Notification Service — pluggable event notification system.

Architecture:
- `NotificationService` is the abstract base class with a single `send()` method.
- `ConsoleMockNotificationService` is the default implementation that logs to stdout.
- A real SMTP/SES/Twilio implementation can be dropped in by:
    1. Subclassing `NotificationService`
    2. Setting NOTIFICATION_BACKEND=smtp (or custom name) in the environment
    3. Updating `get_notification_service()` to return the new class

No imports of Flask app context — all services are pure Python.
"""
import os
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationService(ABC):
    """
    Abstract notification service interface.

    `send()` is the only required method. Implementors can also override
    `_format_subject()` and `_format_body()` if they need custom templates.
    """

    @abstractmethod
    def send(
        self,
        event: str,
        recipient_email: str,
        context: dict,
        subject: Optional[str] = None,
    ) -> None:
        """
        Send a notification for the given event.

        Args:
            event: Event identifier string. Examples:
                   'TRANSFER_COMPLETED', 'LOGIN_FAILED', 'DEPOSIT_COMPLETED',
                   'ACCOUNT_CREATED', 'KYC_STATUS_CHANGED'
            recipient_email: Destination email address.
            context: Dictionary of event-specific data to include in the message.
            subject: Optional override for the message subject/title.
        """
        raise NotImplementedError


class ConsoleMockNotificationService(NotificationService):
    """
    Development-mode notification service that writes to stdout/logs.

    This is intentionally verbose so developers can see what a real email
    would contain without needing SMTP credentials configured.

    To swap in real SMTP later: implement SmtpNotificationService(NotificationService),
    set NOTIFICATION_BACKEND=smtp in env, update get_notification_service().
    """

    EVENT_SUBJECTS = {
        "TRANSFER_COMPLETED": "Money Transfer Confirmation",
        "DEPOSIT_COMPLETED": "Deposit Received",
        "ACCOUNT_CREATED": "New Account Opened",
        "LOGIN_FAILED": "Unusual Login Activity Detected",
        "KYC_STATUS_CHANGED": "Your KYC Status Has Been Updated",
        "ACCOUNT_STATUS_CHANGED": "Account Status Change",
    }

    def send(
        self,
        event: str,
        recipient_email: str,
        context: dict,
        subject: Optional[str] = None,
    ) -> None:
        resolved_subject = subject or self.EVENT_SUBJECTS.get(event, f"BankFlow: {event}")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        body_lines = [
            "━" * 60,
            f"📬  [NOTIFICATION — Console Mock] {timestamp}",
            "━" * 60,
            f"   To      : {recipient_email}",
            f"   Event   : {event}",
            f"   Subject : {resolved_subject}",
            "   Context :",
        ]
        for key, value in context.items():
            body_lines.append(f"      {key}: {value}")
        body_lines.append("━" * 60)

        logger.info("\n".join(body_lines))
        # Also print to stdout so it shows up in gunicorn/render logs
        print("\n".join(body_lines), flush=True)


# ─── Service Factory ──────────────────────────────────────────────────────────

def get_notification_service() -> NotificationService:
    """
    Returns the configured notification service based on NOTIFICATION_BACKEND env var.

    NOTIFICATION_BACKEND=console (default) → ConsoleMockNotificationService
    NOTIFICATION_BACKEND=smtp → SmtpNotificationService (not yet implemented — add here)
    """
    backend = os.getenv("NOTIFICATION_BACKEND", "console").lower().strip()

    if backend == "console":
        return ConsoleMockNotificationService()

    # Extend here:
    # if backend == "smtp":
    #     from app.services.smtp_notification import SmtpNotificationService
    #     return SmtpNotificationService()

    logger.warning(
        f"Unknown NOTIFICATION_BACKEND='{backend}', falling back to ConsoleMockNotificationService."
    )
    return ConsoleMockNotificationService()


# Module-level singleton for reuse across requests (stateless, safe to share)
_notification_service: Optional[NotificationService] = None


def notify(event: str, recipient_email: str, context: dict, subject: Optional[str] = None) -> None:
    """
    Convenience function: get the configured service and send a notification.
    Fire-and-forget — exceptions are caught and logged so they never crash the caller.
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = get_notification_service()

    try:
        _notification_service.send(event, recipient_email, context, subject)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            f"Notification failed for event={event!r} recipient={recipient_email!r}: {exc}",
            exc_info=True
        )

