from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..forms import RegisterForm, LoginForm, EmptyForm
from ..models import User
from ..email_utils import send_verification_email, verify_token
from ..referral_utils import ensure_user_referral_code

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))

    form = RegisterForm()

    if request.method == "GET":
        ref_code = request.args.get("ref", "").strip().upper()
        if ref_code:
            form.referral_code.data = ref_code

    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data.lower()).first()
        if existing:
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("auth.register"))

        referrer = None
        ref_code = (form.referral_code.data or "").strip().upper()
        if ref_code:
            referrer = User.query.filter_by(referral_code=ref_code).first()
            if not referrer:
                flash("Referral code was invalid and has been ignored.", "warning")

        user = User(
            name=form.name.data,
            email=form.email.data.lower(),
            email_verified=False,
            referred_by_id=referrer.id if referrer else None
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.flush()

        ensure_user_referral_code(user)
        db.session.commit()

        send_verification_email(user)

        flash("Account created. Please verify your email before logging in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user and user.check_password(form.password.data):
            if not user.email_verified:
                flash("Please verify your email before logging in.", "warning")
                return redirect(url_for("auth.unverified", email=user.email))

            if not user.is_active_account:
                flash("Your account has been suspended. Contact support.", "danger")
                return redirect(url_for("auth.login"))

            login_user(user)
            flash("Welcome back.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.overview"))

        flash("Invalid credentials.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    email = verify_token(token, "email-verify", max_age=60 * 60 * 24)
    if not email:
        flash("Verification link is invalid or expired.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.login"))

    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        db.session.commit()

    flash("Email verified successfully. You can now log in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/unverified")
def unverified():
    email = request.args.get("email", "")
    form = EmptyForm()
    return render_template("auth/unverified.html", email=email, form=form)

@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    email = request.form.get("email", "").lower().strip()
    user = User.query.filter_by(email=email).first()

    if not user:
        flash("Account not found.", "danger")
        return redirect(url_for("auth.login"))

    if user.email_verified:
        flash("This email is already verified.", "info")
        return redirect(url_for("auth.login"))

    send_verification_email(user)
    flash("Verification email sent again.", "success")
    return redirect(url_for("auth.unverified", email=user.email))

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/forgot-password")
def forgot_password():
    return render_template("auth/page.html", title="Forgot Password", body="Add password reset flow here.")


@auth_bp.route("/reset-password/<token>")
def reset_password(token):
    return render_template("auth/page.html", title="Reset Password", body=f"Reset token received: {token}")


@auth_bp.route("/2fa/setup")
@login_required
def two_factor_setup():
    return render_template("auth/page.html", title="2FA Setup", body="Add authenticator app setup here.")


@auth_bp.route("/kyc")
@login_required
def kyc():
    return render_template("auth/page.html", title="KYC Verification", body="Add KYC upload flow here.")