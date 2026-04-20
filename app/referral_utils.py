import secrets
import string
from datetime import datetime
from flask import current_app

from .extensions import db
from .models import User, Transaction


def generate_unique_referral_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "REF" + "".join(secrets.choice(alphabet) for _ in range(length))
        if not User.query.filter_by(referral_code=code).first():
            return code


def ensure_user_referral_code(user):
    if not user.referral_code:
        user.referral_code = generate_unique_referral_code()
        db.session.add(user)
        db.session.flush()
    return user.referral_code


def process_qualified_referral(referred_user, approved_deposit_amount):
    """
    Called after a deposit is approved.
    Marks a referred user as qualified if eligible,
    and awards the referrer milestone bonus if applicable.
    """
    min_deposit = current_app.config.get("REFERRAL_MIN_QUALIFYING_DEPOSIT", 10.0)
    milestone_size = current_app.config.get("REFERRAL_MILESTONE_SIZE", 10)
    bonus_amount = current_app.config.get("REFERRAL_BONUS_PER_MILESTONE", 20.0)

    if approved_deposit_amount < min_deposit:
        return 0.0

    if referred_user.referral_qualified:
        return 0.0

    if not referred_user.referred_by_id:
        return 0.0

    referred_user.referral_qualified = True
    referred_user.first_qualified_deposit_at = datetime.utcnow()
    db.session.add(referred_user)
    db.session.flush()

    referrer = referred_user.referred_by
    qualified_count = User.query.filter_by(
        referred_by_id=referrer.id,
        referral_qualified=True
    ).count()

    milestones_earned = qualified_count // milestone_size
    already_paid = referrer.referral_reward_milestones_paid or 0
    new_milestones = milestones_earned - already_paid

    if new_milestones <= 0:
        return 0.0

    total_bonus = float(new_milestones * bonus_amount)

    referrer.investment_credit_balance = (referrer.investment_credit_balance or 0.0) + total_bonus
    referrer.referral_reward_milestones_paid = already_paid + new_milestones

    db.session.add(referrer)
    db.session.add(Transaction(
        user_id=referrer.id,
        tx_type="referral_bonus",
        asset="USD",
        amount=total_bonus,
        status="completed",
        notes=(
            f"Referral reward credited: ${total_bonus:.2f} investment credit "
            f"for reaching {milestones_earned * milestone_size} qualified referrals."
        )
    ))

    return total_bonus