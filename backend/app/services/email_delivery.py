import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


email_logger = logging.getLogger("uvicorn.error")


class EmailDeliveryError(Exception):
    pass


def build_invitation_message(
    recipient: str,
    invitation_url: str,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Smart Document RAG hesap daveti"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                "Smart Document RAG çalışma alanına davet edildiniz.",
                "",
                "Hesabınızı oluşturmak için aşağıdaki bağlantıyı açın:",
                invitation_url,
                "",
                (
                    "Bu bağlantı "
                    f"{settings.account_invitation_hours} saat geçerlidir "
                    "ve yalnızca bir kez kullanılabilir."
                ),
                "",
                "Bu daveti beklemiyorsanız e-postayı dikkate almayın.",
            ]
        )
    )
    return message


def build_password_reset_message(
    recipient: str,
    password_reset_url: str,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Smart Document RAG parola yenileme"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                "Smart Document RAG hesabınız için parola yenileme isteği alındı.",
                "",
                "Yeni bir parola belirlemek için aşağıdaki bağlantıyı açın:",
                password_reset_url,
                "",
                (
                    "Bu bağlantı "
                    f"{settings.account_password_reset_minutes} dakika "
                    "geçerlidir ve yalnızca bir kez kullanılabilir."
                ),
                "",
                (
                    "Bu isteği siz yapmadıysanız bağlantıyı "
                    "kullanmayın; mevcut parolanız değişmez."
                ),
            ]
        )
    )
    return message


def deliver_message(message: EmailMessage) -> None:
    if not settings.smtp_host:
        raise EmailDeliveryError(
            "SMTP_HOST must be configured for SMTP delivery.",
        )

    password = (
        settings.smtp_password.get_secret_value()
        if settings.smtp_password is not None
        else None
    )

    if bool(settings.smtp_username) != bool(password):
        raise EmailDeliveryError(
            "SMTP username and password must be configured together.",
        )

    try:
        with smtplib.SMTP(
            host=settings.smtp_host,
            port=settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as smtp:
            smtp.ehlo()

            if settings.smtp_use_tls:
                smtp.starttls(
                    context=ssl.create_default_context(),
                )
                smtp.ehlo()

            if settings.smtp_username and password:
                smtp.login(
                    settings.smtp_username,
                    password,
                )

            smtp.send_message(message)

    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError(
            "Email could not be delivered.",
        ) from error


def send_invitation_email(
    recipient: str,
    invitation_url: str,
) -> None:
    if settings.email_delivery_mode == "console":
        email_logger.info(
            "Development invitation | recipient=%s | url=%s",
            recipient,
            invitation_url,
        )
        return

    deliver_message(
        build_invitation_message(
            recipient=recipient,
            invitation_url=invitation_url,
        )
    )


def send_password_reset_email(
    recipient: str,
    password_reset_url: str,
) -> None:
    if settings.email_delivery_mode == "console":
        email_logger.info(
            "Development password reset | recipient=%s | url=%s",
            recipient,
            password_reset_url,
        )
        return

    deliver_message(
        build_password_reset_message(
            recipient=recipient,
            password_reset_url=password_reset_url,
        )
    )
