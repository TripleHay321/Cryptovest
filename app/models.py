from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)

    is_admin = db.Column(db.Boolean, default=False)
    is_active_account = db.Column(db.Boolean, default=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)

    usd_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship("Transaction", backref="user", lazy=True, cascade="all, delete-orphan")
    investments = db.relationship("Investment", backref="user", lazy=True, cascade="all, delete-orphan")
    tickets = db.relationship("SupportTicket", backref="user", lazy=True, cascade="all, delete-orphan")

    referral_code = db.Column(db.String(20), unique=True, nullable=True, index=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    referral_qualified = db.Column(db.Boolean, default=False)
    first_qualified_deposit_at = db.Column(db.DateTime, nullable=True)

    investment_credit_balance = db.Column(db.Float, default=0.0)
    referral_reward_milestones_paid = db.Column(db.Integer, default=0)

    referred_by = db.relationship(
        "User",
        remote_side=[id],
        backref=db.backref("referred_users", lazy=True)
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class InvestmentPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    min_amount = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    target_return_percent = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(30), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    investments = db.relationship("Investment", backref="plan", lazy=True)


class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("investment_plan.id"), nullable=False)

    amount = db.Column(db.Float, nullable=False)
    projected_return_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    maturity_date = db.Column(db.DateTime, nullable=False)

    @staticmethod
    def create_for_plan(user_id, plan, amount):
        projected = amount + (amount * plan.target_return_percent / 100.0)
        return Investment(
            user_id=user_id,
            plan_id=plan.id,
            amount=amount,
            projected_return_amount=projected,
            maturity_date=datetime.utcnow() + timedelta(days=plan.duration_days),
        )


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    tx_type = db.Column(db.String(30), nullable=False)  # deposit, withdrawal, investment
    asset = db.Column(db.String(20), default="USDT")
    amount = db.Column(db.Float, nullable=False)
    network = db.Column(db.String(50), nullable=True)
    wallet_address = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(30), default="pending")
    reference = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="open")
    admin_reply = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PayoutMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    label = db.Column(db.String(120), nullable=False)
    asset = db.Column(db.String(20), nullable=False, default="USDT")
    network = db.Column(db.String(50), nullable=False)
    wallet_address = db.Column(db.String(255), nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("payout_methods", lazy=True, cascade="all, delete-orphan"))

class WithdrawalVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    payout_method_id = db.Column(db.Integer, db.ForeignKey("payout_method.id"), nullable=False)

    asset = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    code = db.Column(db.String(6), nullable=False)

    used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("withdrawal_verifications", lazy=True, cascade="all, delete-orphan"))
    payout_method = db.relationship("PayoutMethod", backref=db.backref("withdrawal_verifications", lazy=True, cascade="all, delete-orphan"))

