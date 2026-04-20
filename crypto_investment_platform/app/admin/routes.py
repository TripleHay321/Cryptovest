from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from ..decorators import admin_required
from ..extensions import db
from ..forms import PlanForm
from ..models import User, Transaction, InvestmentPlan, SupportTicket, Investment

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_deposits = sum(t.amount for t in Transaction.query.filter_by(tx_type='deposit', status='approved').all())
    total_withdrawals = sum(t.amount for t in Transaction.query.filter_by(tx_type='withdrawal', status='approved').all())
    active_investments = Investment.query.filter_by(status='active').count()
    pending_withdrawals = Transaction.query.filter_by(tx_type='withdrawal', status='pending').count()
    pending_deposits = Transaction.query.filter_by(tx_type='deposit', status='pending').count()
    return render_template('admin/dashboard.html', **locals())


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('admin/user_detail.html', user=user)


@admin_bp.route('/users/<int:user_id>/toggle-status')
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Admin accounts cannot be suspended here.', 'warning')
        return redirect(url_for('admin.users'))
    user.is_active_account = not user.is_active_account
    db.session.commit()
    flash('User status updated.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/deposits')
@login_required
@admin_required
def deposits():
    deposits = Transaction.query.filter_by(tx_type='deposit').order_by(Transaction.created_at.desc()).all()
    return render_template('admin/deposits.html', deposits=deposits)


@admin_bp.route('/withdrawals')
@login_required
@admin_required
def withdrawals():
    withdrawals = Transaction.query.filter_by(tx_type='withdrawal').order_by(Transaction.created_at.desc()).all()
    return render_template('admin/withdrawals.html', withdrawals=withdrawals)


@admin_bp.route('/transactions')
@login_required
@admin_required
def transactions():
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    return render_template('admin/transactions.html', transactions=transactions)


@admin_bp.route('/transactions/<int:tx_id>/approve')
@login_required
@admin_required
def approve_transaction(tx_id):
    tx = Transaction.query.get_or_404(tx_id)
    if tx.status != 'pending':
        flash('Only pending transactions can be approved.', 'warning')
        return redirect(request.referrer or url_for('admin.transactions'))

    tx.status = 'approved'
    if tx.tx_type == 'deposit':
        tx.user.usd_balance += tx.amount
    db.session.commit()
    flash('Transaction approved.', 'success')
    return redirect(request.referrer or url_for('admin.transactions'))


@admin_bp.route('/transactions/<int:tx_id>/reject')
@login_required
@admin_required
def reject_transaction(tx_id):
    tx = Transaction.query.get_or_404(tx_id)
    if tx.status != 'pending':
        flash('Only pending transactions can be rejected.', 'warning')
        return redirect(request.referrer or url_for('admin.transactions'))

    tx.status = 'rejected'
    if tx.tx_type == 'withdrawal':
        tx.user.usd_balance += tx.amount
    db.session.commit()
    flash('Transaction rejected.', 'success')
    return redirect(request.referrer or url_for('admin.transactions'))


@admin_bp.route('/plans', methods=['GET', 'POST'])
@login_required
@admin_required
def plans():
    form = PlanForm()
    if form.validate_on_submit():
        plan = InvestmentPlan(
            name=form.name.data,
            description=form.description.data,
            min_amount=form.min_amount.data,
            duration_days=int(form.duration_days.data),
            target_return_percent=form.target_return_percent.data,
            risk_level=form.risk_level.data,
        )
        db.session.add(plan)
        db.session.commit()
        flash('Plan created successfully.', 'success')
        return redirect(url_for('admin.plans'))
    plans = InvestmentPlan.query.order_by(InvestmentPlan.created_at.desc()).all()
    return render_template('admin/plans.html', form=form, plans=plans)


@admin_bp.route('/plans/<int:plan_id>/toggle')
@login_required
@admin_required
def toggle_plan(plan_id):
    plan = InvestmentPlan.query.get_or_404(plan_id)
    plan.is_active = not plan.is_active
    db.session.commit()
    flash('Plan visibility updated.', 'success')
    return redirect(url_for('admin.plans'))


@admin_bp.route('/support', methods=['GET', 'POST'])
@login_required
@admin_required
def support():
    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    if request.method == 'POST':
        ticket_id = int(request.form.get('ticket_id'))
        reply = request.form.get('reply', '').strip()
        ticket = SupportTicket.query.get_or_404(ticket_id)
        ticket.admin_reply = reply
        ticket.status = 'answered' if reply else ticket.status
        db.session.commit()
        flash('Ticket updated.', 'success')
        return redirect(url_for('admin.support'))
    return render_template('admin/support.html', tickets=tickets)


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('admin/settings.html')


@admin_bp.route('/kyc')
@login_required
@admin_required
def kyc():
    return render_template('admin/kyc.html')


@admin_bp.route('/content')
@login_required
@admin_required
def content():
    return render_template('admin/content.html')


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    return render_template('admin/reports.html')


@admin_bp.route('/notifications')
@login_required
@admin_required
def notifications():
    return render_template('admin/notifications.html')


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    return render_template('admin/audit_logs.html')


@admin_bp.route('/roles')
@login_required
@admin_required
def roles():
    return render_template('admin/roles.html')
