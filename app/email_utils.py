from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app, url_for
from flask_mail import Message
from .extensions import mail


def generate_token(email, salt):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(email, salt=salt)


def verify_token(token, salt, max_age=3600):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = serializer.loads(token, salt=salt, max_age=max_age)
        return email
    except (BadSignature, SignatureExpired):
        return None


def send_email(subject, recipients, html_body, text_body=None):
    msg = Message(
        subject=subject,
        recipients=recipients,
        html=html_body,
        body=text_body or ""
    )
    mail.send(msg)


def send_verification_email(user):
    token = generate_token(user.email, "email-verify")
    verify_link = url_for("auth.verify_email", token=token, _external=True)

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
        <h2>Verify your email</h2>
        <p>Hello {user.name},</p>
        <p>Click the button below to verify your account email address.</p>
        <p>
            <a href="{verify_link}" style="display:inline-block;padding:12px 18px;background:#2f68ff;color:#fff;text-decoration:none;border-radius:8px;">
                Verify Email
            </a>
        </p>
        <p>If you did not create this account, you can ignore this email.</p>
    </div>
    """

    send_email(
        subject="Verify your CryptoVest account",
        recipients=[user.email],
        html_body=html,
        text_body=f"Verify your account: {verify_link}"
    )


def send_withdrawal_code_email(user, code, amount, asset):
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
        <h2>Withdrawal confirmation code</h2>
        <p>Hello {user.name},</p>
        <p>You requested a withdrawal of <strong>{amount:.2f} {asset}</strong>.</p>
        <p>Your confirmation code is:</p>
        <div style="font-size:32px;font-weight:bold;letter-spacing:6px;margin:20px 0;color:#2f68ff;">
            {code}
        </div>
        <p>This code expires in 10 minutes.</p>
        <p>If you did not request this withdrawal, secure your account immediately.</p>
    </div>
    """

    send_email(
        subject="Confirm your withdrawal",
        recipients=[user.email],
        html_body=html,
        text_body=f"Your withdrawal confirmation code is: {code}"
    )