import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    def send(self, to: str, subject: str, html: str) -> None:
        provider = settings.email_provider.lower()
        if provider == "console" or settings.debug:
            logger.info("[email] to=%s subject=%s\n%s", to, subject, html)
            return
        if provider == "resend":
            self._send_resend(to, subject, html)
            return
        if provider == "smtp":
            self._send_smtp(to, subject, html)
            return
        logger.warning("Unknown email provider: %s", provider)

    def _send_resend(self, to: str, subject: str, html: str) -> None:
        if not settings.resend_api_key:
            raise RuntimeError("RESEND_API_KEY not configured")
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={"from": settings.smtp_from, "to": [to], "subject": subject, "html": html},
            )
            resp.raise_for_status()

    def _send_smtp(self, to: str, subject: str, html: str) -> None:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        if not settings.smtp_host:
            raise RuntimeError("SMTP not configured")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from, [to], msg.as_string())

    def send_password_reset(self, to: str, reset_url: str) -> None:
        self.send(
            to,
            "Đặt lại mật khẩu TAPTOT",
            f"<p>Nhấn vào link để đặt lại mật khẩu:</p><p><a href='{reset_url}'>{reset_url}</a></p>",
        )

    def send_verification(self, to: str, verify_url: str) -> None:
        self.send(
            to,
            "Xác thực email TAPTOT",
            f"<p>Nhấn vào link để xác thực email:</p><p><a href='{verify_url}'>{verify_url}</a></p>",
        )
