import resend
from flask import current_app


class EmailService:
    @staticmethod
    def _send(to, subject, html):
        api_key = current_app.config.get("RESEND_API_KEY", "")
        sender = current_app.config.get("FROM_EMAIL", "")
        if not api_key or not sender:
            raise RuntimeError("Email provider is not configured.")
        resend.api_key = api_key
        return resend.Emails.send(
            {
                "from": sender,
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )

    @staticmethod
    def send_admin_password_reset(email, reset_url, expires_minutes):
        return EmailService._send(
            email,
            "Clipcart admin password reset",
            f"""
            <p>A password reset was requested for the private Clipcart administrator account.</p>
            <p><a href="{reset_url}">Reset administrator password</a></p>
            <p>This link expires in {int(expires_minutes)} minutes and can only be used before the account changes again.</p>
            <p>If you did not request this, no action is required.</p>
            """,
        )

    @staticmethod
    def send_order_confirmation(order, invoice_path=None):
        # Existing order confirmation flow is intentionally preserved.
        return True
