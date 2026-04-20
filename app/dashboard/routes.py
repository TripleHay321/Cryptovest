from datetime import datetime, timedelta
import random
from collections import OrderedDict, defaultdict
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user

from ..extensions import db
from ..forms import (
    DepositForm, WithdrawalForm, InvestmentForm,
    ProfileForm, PasswordChangeForm, SupportForm,
    PayoutMethodForm, VerifyWithdrawalCodeForm
)
from ..models import (
    User, InvestmentPlan, Investment, Transaction,
    SupportTicket, PayoutMethod, WithdrawalVerification
)
from ..email_utils import send_withdrawal_code_email
from ..referral_utils import ensure_user_referral_code

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def overview():
    transactions = (
        Transaction.query
        .filter_by(user_id=current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(5)
        .all()
    )

    investments = Investment.query.filter_by(user_id=current_user.id).all()
    total_invested = sum(i.amount for i in investments)
    projected_value = sum(i.projected_return_amount for i in investments)

    return render_template(
        "dashboard/overview.html",
        transactions=transactions,
        investments=investments,
        total_invested=total_invested,
        projected_value=projected_value,
    )

@dashboard_bp.route("/portfolio-trend-data")
@login_required
def portfolio_trend_data():
    investments = (
        Investment.query
        .filter_by(user_id=current_user.id)
        .order_by(Investment.created_at.asc())
        .all()
    )

    # Group by date
    daily = OrderedDict()

    for inv in investments:
        day = inv.created_at.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {
                "invested": 0.0,
                "projected": 0.0
            }

        daily[day]["invested"] += float(inv.amount)
        daily[day]["projected"] += float(inv.projected_return_amount)

    labels = []
    invested_series = []
    projected_series = []

    running_invested = 0.0
    running_projected = 0.0

    for day, values in daily.items():
        running_invested += values["invested"]
        running_projected += values["projected"]

        labels.append(day)
        invested_series.append(round(running_invested, 2))
        projected_series.append(round(running_projected, 2))

    if not labels:
        labels = ["No Data"]
        invested_series = [0]
        projected_series = [0]

    return jsonify({
        "labels": labels,
        "invested": invested_series,
        "projected": projected_series
    })


@dashboard_bp.route("/wallet")
@login_required
def wallet():
    transactions = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return render_template("dashboard/wallet.html", transactions=transactions)


@dashboard_bp.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    form = DepositForm()
    if form.validate_on_submit():
        tx = Transaction(
            user_id=current_user.id,
            tx_type='deposit',
            asset=form.asset.data,
            amount=form.amount.data,
            network=form.network.data,
            reference=form.reference.data,
            status='pending',
            notes='Awaiting blockchain payment / admin confirmation.'
        )
        db.session.add(tx)
        db.session.commit()
        return redirect(url_for('dashboard.deposit_instructions', tx_id=tx.id))

    return render_template('dashboard/deposit.html', form=form)

@dashboard_bp.route('/deposit/<int:tx_id>/instructions')
@login_required
def deposit_instructions(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id, tx_type='deposit').first_or_404()

    # Demo static addresses - replace with provider-generated wallet addresses or hosted checkout
    deposit_addresses = {
        ('USDT', 'TRC20'): 'TAwbSEU37yj6om9T7X2tCQ3jbNnwMt1Lqs',
        ('USDT', 'ERC20'): '0xcba17fc12dfba5d50f471518d2ffb74c5a63d6a3',
        ('USDT', 'BEP20'): '0xcba17fc12dfba5d50f471518d2ffb74c5a63d6a3',
        ('USDT', 'ARB'): '0xcba17fc12dfba5d50f471518d2ffb74c5a63d6a3',
        ('BTC', 'BTC'): '16AX9f2CPwkKXFyQCXeMwf1u16MeXmjJox',
        ('BTC', 'BEP20'): '0xcba17fc12dfba5d50f471518d2ffb74c5a63d6a3',
        ('ETH', 'ERC20'): '0xcba17fc12dfba5d50f471518d2ffb74c5a63d6a3',
        ('ETH', 'BEP20'): '0xcba17fc12dfba5d50f471518d2ffb74c5a63d6a3',
        ('ETH', 'ARB'): '0xcba17fc12dfba5d50f471518d2ffb74c5a63d6a3',
    }

    wallet_address = deposit_addresses.get((tx.asset, tx.network), 'Provider wallet not configured')

    return render_template(
        'dashboard/deposit_instructions.html',
        tx=tx,
        wallet_address=wallet_address
    )

@dashboard_bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    if not current_user.email_verified:
        flash('Please verify your email before making withdrawals.', 'warning')
        return redirect(url_for('auth.unverified', email=current_user.email))

    form = WithdrawalForm()
    payout_methods = PayoutMethod.query.filter_by(user_id=current_user.id, is_active=True).all()
    form.payout_method_id.choices = [
        (pm.id, f"{pm.label} — {pm.asset}/{pm.network} — {pm.wallet_address[:12]}...")
        for pm in payout_methods
    ]

    if not payout_methods:
        flash('Please add a payout wallet before requesting a withdrawal.', 'warning')
        return redirect(url_for('dashboard.payout_methods'))

    if form.validate_on_submit():
        payout_method = PayoutMethod.query.filter_by(
            id=form.payout_method_id.data,
            user_id=current_user.id,
            is_active=True
        ).first()

        if not payout_method:
            flash('Invalid payout method selected.', 'danger')
            return redirect(url_for('dashboard.withdraw'))

        if form.amount.data > current_user.usd_balance:
            flash('Insufficient balance.', 'danger')
            return redirect(url_for('dashboard.withdraw'))

        code = str(random.randint(100000, 999999))
        verification = WithdrawalVerification(
            user_id=current_user.id,
            payout_method_id=payout_method.id,
            asset=form.asset.data,
            amount=form.amount.data,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            used=False
        )

        db.session.add(verification)
        db.session.commit()

        send_withdrawal_code_email(current_user, code, form.amount.data, form.asset.data)

        flash('A 6-digit withdrawal confirmation code has been sent to your email.', 'info')
        return redirect(url_for('dashboard.confirm_withdrawal', verification_id=verification.id))

    return render_template('dashboard/withdraw.html', form=form, payout_methods=payout_methods)

@dashboard_bp.route('/withdraw/confirm/<int:verification_id>', methods=['GET', 'POST'])
@login_required
def confirm_withdrawal(verification_id):
    verification = WithdrawalVerification.query.filter_by(
        id=verification_id,
        user_id=current_user.id,
        used=False
    ).first_or_404()

    form = VerifyWithdrawalCodeForm()

    if verification.expires_at < datetime.utcnow():
        flash('Verification code expired. Please request withdrawal again.', 'danger')
        return redirect(url_for('dashboard.withdraw'))

    if form.validate_on_submit():
        if form.code.data != verification.code:
            flash('Invalid verification code.', 'danger')
            return redirect(url_for('dashboard.confirm_withdrawal', verification_id=verification.id))

        if verification.amount > current_user.usd_balance:
            flash('Insufficient balance.', 'danger')
            return redirect(url_for('dashboard.withdraw'))

        current_user.usd_balance -= verification.amount

        tx = Transaction(
            user_id=current_user.id,
            tx_type='withdrawal',
            asset=verification.asset,
            amount=verification.amount,
            network=verification.payout_method.network,
            wallet_address=verification.payout_method.wallet_address,
            status='pending',
            notes=f'Withdrawal email verified. Payout wallet: {verification.payout_method.label}'
        )

        verification.used = True
        db.session.add(tx)
        db.session.commit()

        flash('Withdrawal confirmed and submitted successfully.', 'success')
        return redirect(url_for('dashboard.transactions'))

    return render_template(
        'dashboard/withdraw_confirm.html',
        form=form,
        verification=verification
    )

@dashboard_bp.route('/withdraw/confirm/<int:verification_id>/resend', methods=['POST'])
@login_required
def resend_withdrawal_code(verification_id):
    verification = WithdrawalVerification.query.filter_by(
        id=verification_id,
        user_id=current_user.id,
        used=False
    ).first_or_404()

    if verification.expires_at < datetime.utcnow():
        flash('This verification request expired. Start a new withdrawal request.', 'warning')
        return redirect(url_for('dashboard.withdraw'))

    code = str(random.randint(100000, 999999))
    verification.code = code
    verification.expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    send_withdrawal_code_email(current_user, code, verification.amount, verification.asset)
    flash('A new verification code has been sent to your email.', 'success')
    return redirect(url_for('dashboard.confirm_withdrawal', verification_id=verification.id))

@dashboard_bp.route('/investments', methods=['GET', 'POST'])
@login_required
def investments():
    plans = InvestmentPlan.query.filter_by(is_active=True).all()
    form = InvestmentForm()

    if form.validate_on_submit():
        selected_plan_id = int(request.form.get('plan_id') or 0)
        plan = InvestmentPlan.query.get_or_404(selected_plan_id)
        amount = float(form.amount.data)

        if amount < plan.min_amount:
            flash(f'Minimum amount for {plan.name} is ${plan.min_amount:.2f}.', 'danger')
            return redirect(url_for('dashboard.investments'))

        investable_total = (current_user.usd_balance or 0.0) + (current_user.investment_credit_balance or 0.0)
        if amount > investable_total:
            flash('Insufficient investable balance.', 'danger')
            return redirect(url_for('dashboard.investments'))

        current_credit = current_user.investment_credit_balance or 0.0
        current_cash = current_user.usd_balance or 0.0

        credit_used = min(current_credit, amount)
        cash_used = amount - credit_used

        current_user.investment_credit_balance = current_credit - credit_used
        current_user.usd_balance = current_cash - cash_used

        inv = Investment.create_for_plan(current_user.id, plan, amount)

        db.session.add(inv)
        db.session.add(Transaction(
            user_id=current_user.id,
            tx_type='investment',
            asset='USD',
            amount=amount,
            status='completed',
            notes=(
                f'Investment created in {plan.name}. '
                f'Cash used: ${cash_used:.2f}. '
                f'Investment credit used: ${credit_used:.2f}.'
            )
        ))
        db.session.commit()

        flash('Investment created successfully.', 'success')
        return redirect(url_for('dashboard.investments'))

    my_investments = Investment.query.filter_by(user_id=current_user.id).order_by(Investment.created_at.desc()).all()
    investable_total = (current_user.usd_balance or 0.0) + (current_user.investment_credit_balance or 0.0)

    return render_template(
        'dashboard/investments.html',
        plans=plans,
        form=form,
        my_investments=my_investments,
        investable_total=investable_total
    )


@dashboard_bp.route("/investments/<int:investment_id>")
@login_required
def investment_detail(investment_id):
    investment = Investment.query.filter_by(id=investment_id, user_id=current_user.id).first_or_404()
    return render_template("dashboard/investment_detail.html", investment=investment)


@dashboard_bp.route("/transactions")
@login_required
def transactions():
    txs = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return render_template("dashboard/transactions.html", transactions=txs)


@dashboard_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(name=current_user.name)
    if form.validate_on_submit():
        current_user.name = form.name.data
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("dashboard.profile"))
    return render_template("dashboard/profile.html", form=form)


@dashboard_bp.route("/security", methods=["GET", "POST"])
@login_required
def security():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("dashboard.security"))

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("Password updated successfully.", "success")
        return redirect(url_for("dashboard.security"))

    return render_template("dashboard/security.html", form=form)


@dashboard_bp.route("/support", methods=["GET", "POST"])
@login_required
def support():
    form = SupportForm()
    if form.validate_on_submit():
        ticket = SupportTicket(
            user_id=current_user.id,
            subject=form.subject.data,
            message=form.message.data,
        )
        db.session.add(ticket)
        db.session.commit()
        flash("Support ticket created.", "success")
        return redirect(url_for("dashboard.support"))

    tickets = (
        SupportTicket.query.filter_by(user_id=current_user.id)
        .order_by(SupportTicket.created_at.desc())
        .all()
    )
    return render_template("dashboard/support.html", form=form, tickets=tickets)


@dashboard_bp.route("/performance")
@login_required
def performance():
    investments = (
        Investment.query
        .filter_by(user_id=current_user.id)
        .order_by(Investment.created_at.asc())
        .all()
    )

    total_invested = sum(inv.amount for inv in investments)
    projected_value = sum(inv.projected_return_amount for inv in investments)
    projected_profit = projected_value - total_invested

    return render_template(
        "dashboard/performance.html",
        investments=investments,
        total_invested=total_invested,
        projected_value=projected_value,
        projected_profit=projected_profit
    )

@dashboard_bp.route("/performance/data")
@login_required
def performance_data():
    investments = (
        Investment.query
        .filter_by(user_id=current_user.id)
        .order_by(Investment.created_at.asc())
        .all()
    )

    # --- Build cumulative timeline from real investments ---
    daily_changes = OrderedDict()

    for inv in investments:
        day = inv.created_at.strftime("%Y-%m-%d")
        if day not in daily_changes:
            daily_changes[day] = {
                "invested": 0.0,
                "projected": 0.0
            }

        daily_changes[day]["invested"] += float(inv.amount)
        daily_changes[day]["projected"] += float(inv.projected_return_amount)

    labels = []
    invested_series = []
    projected_series = []

    running_invested = 0.0
    running_projected = 0.0

    for day, values in daily_changes.items():
        running_invested += values["invested"]
        running_projected += values["projected"]

        labels.append(day)
        invested_series.append(round(running_invested, 2))
        projected_series.append(round(running_projected, 2))

    # If no investments yet
    if not labels:
        labels = ["No Data"]
        invested_series = [0]
        projected_series = [0]

    # --- Allocation by actual plan ---
    plan_totals = defaultdict(float)
    plan_colors = []

    risk_colors = {
        "Low": "#18d39e",
        "Medium": "#29d3ff",
        "High": "#f3c969"
    }

    for inv in investments:
        plan_name = inv.plan.name
        plan_totals[plan_name] += float(inv.amount)

    allocation_labels = []
    allocation_values = []
    allocation_colors = []

    # Use first matching investment for plan risk color
    for plan_name, total in plan_totals.items():
        allocation_labels.append(plan_name)
        allocation_values.append(round(total, 2))

        matching_inv = next((i for i in investments if i.plan.name == plan_name), None)
        if matching_inv:
            allocation_colors.append(risk_colors.get(matching_inv.plan.risk_level, "#3d8bff"))
        else:
            allocation_colors.append("#3d8bff")

    if not allocation_labels:
        allocation_labels = ["No Allocation"]
        allocation_values = [0]
        allocation_colors = ["#3d8bff"]

    total_invested = sum(inv.amount for inv in investments)
    projected_value = sum(inv.projected_return_amount for inv in investments)
    projected_profit = projected_value - total_invested

    return jsonify({
        "summary": {
            "total_invested": round(total_invested, 2),
            "projected_value": round(projected_value, 2),
            "projected_profit": round(projected_profit, 2)
        },
        "trend": {
            "labels": labels,
            "invested": invested_series,
            "projected": projected_series
        },
        "allocation": {
            "labels": allocation_labels,
            "values": allocation_values,
            "colors": allocation_colors
        }
    })

@dashboard_bp.route("/notifications")
@login_required
def notifications():
    transactions = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(20)
        .all()
    )

    tickets = (
        SupportTicket.query.filter_by(user_id=current_user.id)
        .order_by(SupportTicket.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard/notifications.html",
        transactions=transactions,
        tickets=tickets
    )

@dashboard_bp.route('/payout-methods', methods=['GET', 'POST'])
@login_required
def payout_methods():
    form = PayoutMethodForm()

    if form.validate_on_submit():
        payout = PayoutMethod(
            user_id=current_user.id,
            label=form.label.data,
            asset=form.asset.data,
            network=form.network.data,
            wallet_address=form.wallet_address.data,
            is_active=True
        )
        db.session.add(payout)
        db.session.commit()
        flash('Payout wallet added successfully.', 'success')
        return redirect(url_for('dashboard.payout_methods'))

    methods = PayoutMethod.query.filter_by(user_id=current_user.id).order_by(PayoutMethod.created_at.desc()).all()
    return render_template('dashboard/payout_methods.html', form=form, methods=methods)

@dashboard_bp.route('/payout-methods/<int:method_id>/delete')
@login_required
def delete_payout_method(method_id):
    method = PayoutMethod.query.filter_by(id=method_id, user_id=current_user.id).first_or_404()
    db.session.delete(method)
    db.session.commit()
    flash('Payout wallet removed.', 'info')
    return redirect(url_for('dashboard.payout_methods'))



@dashboard_bp.route('/referrals')
@login_required
def referrals():
    if not current_user.referral_code:
        ensure_user_referral_code(current_user)
        db.session.commit()

    milestone_size = current_app.config.get("REFERRAL_MILESTONE_SIZE", 10)
    bonus_per_milestone = current_app.config.get("REFERRAL_BONUS_PER_MILESTONE", 20.0)

    referred_users = (
        User.query
        .filter_by(referred_by_id=current_user.id)
        .order_by(User.created_at.desc())
        .all()
    )

    total_referrals = len(referred_users)
    qualified_referrals = sum(1 for u in referred_users if u.referral_qualified)
    rewards_earned = current_user.referral_reward_milestones_paid or 0
    total_bonus_earned = rewards_earned * bonus_per_milestone

    remainder = qualified_referrals % milestone_size
    progress_count = milestone_size if qualified_referrals > 0 and remainder == 0 else remainder
    progress_percent = (progress_count / milestone_size) * 100 if milestone_size else 0
    remaining_to_next = 0 if qualified_referrals > 0 and remainder == 0 else (milestone_size - remainder)

    referral_link = url_for("auth.register", ref=current_user.referral_code, _external=True)

    return render_template(
        "dashboard/referrals.html",
        referral_code=current_user.referral_code,
        referral_link=referral_link,
        total_referrals=total_referrals,
        qualified_referrals=qualified_referrals,
        total_bonus_earned=total_bonus_earned,
        investment_credit_balance=current_user.investment_credit_balance or 0.0,
        referred_users=referred_users[:20],
        milestone_size=milestone_size,
        bonus_per_milestone=bonus_per_milestone,
        progress_count=progress_count,
        progress_percent=progress_percent,
        remaining_to_next=remaining_to_next
    )


@dashboard_bp.route('/referrals/data')
@login_required
def referrals_data():
    referred_users = (
        User.query
        .filter_by(referred_by_id=current_user.id)
        .order_by(User.created_at.asc())
        .all()
    )

    signup_daily = OrderedDict()
    qualified_daily = OrderedDict()

    for user in referred_users:
        signup_day = user.created_at.strftime("%Y-%m-%d")
        signup_daily[signup_day] = signup_daily.get(signup_day, 0) + 1

        if user.referral_qualified and user.first_qualified_deposit_at:
            q_day = user.first_qualified_deposit_at.strftime("%Y-%m-%d")
            qualified_daily[q_day] = qualified_daily.get(q_day, 0) + 1

    all_days = sorted(set(list(signup_daily.keys()) + list(qualified_daily.keys())))

    if not all_days:
        return jsonify({
            "labels": ["No Data"],
            "signups": [0],
            "qualified": [0],
            "breakdown_labels": ["Pending", "Qualified"],
            "breakdown_values": [0, 0]
        })

    signups_running = 0
    qualified_running = 0
    signups_series = []
    qualified_series = []

    for day in all_days:
        signups_running += signup_daily.get(day, 0)
        qualified_running += qualified_daily.get(day, 0)
        signups_series.append(signups_running)
        qualified_series.append(qualified_running)

    total_referrals = len(referred_users)
    qualified_referrals = sum(1 for u in referred_users if u.referral_qualified)
    pending_referrals = total_referrals - qualified_referrals

    return jsonify({
        "labels": all_days,
        "signups": signups_series,
        "qualified": qualified_series,
        "breakdown_labels": ["Pending", "Qualified"],
        "breakdown_values": [pending_referrals, qualified_referrals]
    })