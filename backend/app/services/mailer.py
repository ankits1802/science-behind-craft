import asyncio
import logging
from dataclasses import dataclass
from email.utils import formataddr

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    text: str
    html: str | None = None


def mail_configured() -> bool:
    return bool((get_settings().mail_from_address or "").strip())


def _send_sync(mail: Mail) -> str | None:
    import boto3

    settings = get_settings()
    client = boto3.client("sesv2", region_name=settings.mail_ses_region)
    body: dict[str, dict[str, str]] = {"Text": {"Data": mail.text, "Charset": "UTF-8"}}
    if mail.html:
        body["Html"] = {"Data": mail.html, "Charset": "UTF-8"}
    request: dict = {
        "FromEmailAddress": formataddr((settings.mail_from_name, settings.mail_from_address or "")),
        "Destination": {"ToAddresses": [mail.to]},
        "Content": {"Simple": {"Subject": {"Data": mail.subject, "Charset": "UTF-8"}, "Body": body}},
    }
    if settings.mail_reply_to:
        request["ReplyToAddresses"] = [settings.mail_reply_to]
    if settings.mail_ses_configuration_set:
        request["ConfigurationSetName"] = settings.mail_ses_configuration_set
    response = client.send_email(**request)
    return response.get("MessageId")


async def send(mail: Mail) -> bool:
    if not mail_configured():
        logger.warning("mail is not configured; a %r message was not sent", mail.subject)
        return False
    try:
        message_id = await asyncio.to_thread(_send_sync, mail)
    except Exception:
        logger.exception("mail: SES refused or could not be reached")
        return False
    logger.info("mail sent", extra={"messageId": message_id})
    return True


def reset_link_mail(to: str, link: str, minutes: int) -> Mail:
    text = (
        f"Someone asked to reset the KalaVigyan password for {to}.\n\n"
        f"Open this link within {minutes} minutes to choose a new password:\n{link}\n\n"
        "If this was not you, ignore this message; your password stays the same."
    )
    return Mail(to=to, subject="Reset your KalaVigyan password", text=text)


def invite_link_mail(to: str, link: str, minutes: int) -> Mail:
    text = (
        f"An administrator created a KalaVigyan account for {to}.\n\n"
        f"Open this link within {minutes} minutes to set your password:\n{link}"
    )
    return Mail(to=to, subject="Set your KalaVigyan password", text=text)


def signup_link_mail(to: str, link: str, minutes: int) -> Mail:
    hours = max(1, minutes // 60)
    text = (
        f"Someone asked for a KalaVigyan account for {to}.\n\n"
        f"Open this link within {hours} hours to confirm the address and choose your password:\n{link}\n\n"
        "An administrator then reviews the request. If you did not ask for this, ignore this email."
    )
    return Mail(to=to, subject="Confirm your KalaVigyan sign-up", text=text)


def password_changed_mail(to: str) -> Mail:
    text = (
        f"The password for the KalaVigyan account {to} was just changed. Every other device was signed out.\n\n"
        "If this was not you, reset the password now and tell the administrator."
    )
    return Mail(to=to, subject="Your KalaVigyan password was changed", text=text)
