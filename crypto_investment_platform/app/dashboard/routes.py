from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..forms import DepositForm, WithdrawalForm, InvestmentForm, ProfileForm, PasswordChangeForm, SupportForm
from ..models import InvestmentPlan, Investment, Transaction, SupportTicket

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def overview():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).limit(5).all()
    investments = Investment.query.filter_by(user_id=current_user.id).all()
    active_investments = [i for i in investments if i.status == 'active']
    total_invested = sum(i.amount for i in investments)
    projected_value = sum(i.projected_return_amount for i in investments)
    return render_template(
        'dashboard/overview.html',
        transactions=transactions,
        investments=active_investments,
        total_invested=total_invested,
        projected_value=projected_value,
    )


@dashboard_bp.route('/wallet')
@login_required
def wallet():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).all()
    return render_template('dashboard/wallet.html', transactions=transactions)


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
            notes='Awaiting admin review / payment confirmation.'
        )
        db.session.add(tx)
        db.session.commit()
        flash('Deposit request submitted. It will appear once approved.', 'success')
        return redirect(url_for('dashboard.wallet'))
    return render_template('dashboard/deposit.html', form=form)


@dashboard_bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    form = WithdrawalForm()
    if form.validate_on_submit():
        if form.amount.data > current_user.usd_balance:
            flash('Insufficient balance.', 'danger')
            return redirect(url_for('dashboard.withdraw'))
        current_user.usd_balance -= form.amount.data
        tx = Transaction(
            user_id=current_user.id,
            tx_type='withdrawal',
            asset=form.asset.data,
            amount=form.amount.data,
            network=form.network.data,
            wallet_address=form.wallet_address.data,
            status='pending',
            notes='Pending admin approval.'
        )
        db.session.add(tx)
        db.session.commit()
        flash('Withdrawal request submitted.', 'success')
        return redirect(url_for('dashboard.wallet'))
    return render_template('dashboard/withdraw.html', form=form)


@dashboard_bp.route('/investments', methods=['GET', 'POST'])
@login_required
def investments():
    plans = InvestmentPlan.query.filter_by(is_active=True).all()
    form = InvestmentForm()
    if form.validate_on_submit():
        selected_plan_id = int((__import__('flask').request.form.get('plan_id') or 0))
        plan = InvestmentPlan.query.get_or_404(selected_plan_id)
        amount = form.amount.data
        if amount < plan.min_amount:
            flash(f'Minimum amount for {plan.name} is ${plan.min_amount:.2f}.', 'danger')
            return redirect(url_for('dashboard.investments'))
        if amount > current_user.usd_balance:
            flash('Insufficient balance.', 'danger')
            return redirect(url_for('dashboard.investments'))
        inv = Investment.create_for_plan(current_user.id, plan, amount)
        current_user.usd_balance -= amount
        db.session.add(inv)
        db.session.add(Transaction(
            user_id=current_user.id,
            tx_type='investment',
            asset='USD',
            amount=amount,
            status='completed',
            notes=f'Investment created in {plan.name}.'
        ))
        db.session.commit()
        flash('Investment created successfully.', 'success')
        return redirect(url_for('dashboard.investments'))

    my_investments = Investment.query.filter_by(user_id=current_user.id).order_by(Investment.created_at.desc()).all()
    return render_template('dashboard/investments.html', plans=plans, form=form, my_investments=my_investments)


@dashboard_bp.route('/investments/<int:investment_id>')
@login_required
def investment_detail(investment_id):
    investment = Investment.query.filter_by(id=investment_id, user_id=current_user.id).first_or_404()
    return render_template('dashboard/investment_detail.html', investment=investment)


@dashboard_bp.route('/transactions')
@login_required
def transactions():
    txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).all()
    return render_template('dashboard/transactions.html', transactions=txs)


@dashboard_bp.route('/performance')
@login_required
def performance():
    investments = Investment.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard/performance.html', investments=investments)


@dashboard_bp.route('/notifications')
@login_required
def notifications():
    txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).limit(10).all()
    return render_template('dashboard/notifications.html', transactions=txs)


@dashboard_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(name=current_user.name)
    if form.validate_on_submit():
        current_user.name = form.name.data
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('dashboard.profile'))
    return render_template('dashboard/profile.html', form=form)


@dashboard_bp.route('/security', methods=['GET', 'POST'])
@login_required
def security():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('dashboard.security'))
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password updated successfully.', 'success')
        return redirect(url_for('dashboard.security'))
    return render_template('dashboard/security.html', form=form)


@dashboard_bp.route('/payout-methods')
@login_required
def payout_methods():
    return render_template('dashboard/payout_methods.html')


@dashboard_bp.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    form = SupportForm()
    if form.validate_on_submit():
        ticket = SupportTicket(user_id=current_user.id, subject=form.subject.data, message=form.message.data)
        db.session.add(ticket)
        db.session.commit()
        flash('Support ticket created.', 'success')
        return redirect(url_for('dashboard.support'))
    tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(SupportTicket.created_at.desc()).all()
    return render_template('dashboard/support.html', form=form, tickets=tickets)


@dashboard_bp.route('/referrals')
@login_required
def referrals():
    return render_template('dashboard/referrals.html')
