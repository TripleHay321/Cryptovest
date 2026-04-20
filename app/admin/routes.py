from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from ..decorators import admin_required
from ..extensions import db
from ..forms import PlanForm
from ..models import User, Transaction, InvestmentPlan, SupportTicket, Investment
from ..referral_utils import process_qualified_referral

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_deposits = sum(t.amount for t in Transaction.query.filter_by(tx_type="deposit", status="approved").all())
    total_withdrawals = sum(t.amount for t in Transaction.query.filter_by(tx_type="withdrawal", status="approved").all())
    active_investments = Investment.query.filter_by(status="active").count()
    pending_deposits = Transaction.query.filter_by(tx_type="deposit", status="pending").count()
    pending_withdrawals = Transaction.query.filter_by(tx_type="withdrawal", status="pending").count()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        active_investments=active_investments,
        pending_deposits=pending_deposits,
        pending_withdrawals=pending_withdrawals,
    )


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/<int:user_id>")
@login_required
@admin_required
def user_detail(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_detail.html", user=user)


@admin_bp.route("/users/<int:user_id>/toggle-status")
@login_required
@admin_required
def toggle_user_status(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.is_admin:
        flash("Admin accounts cannot be suspended here.", "warning")
        return redirect(url_for("admin.user_detail", user_id=user.id))

    user.is_active_account = not user.is_active_account
    db.session.commit()
    flash("User status updated.", "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@admin_bp.route("/deposits")
@login_required
@admin_required
def deposits():
    deposits = Transaction.query.filter_by(tx_type="deposit").order_by(Transaction.created_at.desc()).all()
    return render_template("admin/deposits.html", deposits=deposits)


@admin_bp.route("/withdrawals")
@login_required
@admin_required
def withdrawals():
    withdrawals = Transaction.query.filter_by(tx_type="withdrawal").order_by(Transaction.created_at.desc()).all()
    return render_template("admin/withdrawals.html", withdrawals=withdrawals)


@admin_bp.route("/transactions")
@login_required
@admin_required
def transactions():
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    return render_template("admin/transactions.html", transactions=transactions)


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
        process_qualified_referral(tx.user, tx.amount)

    db.session.commit()
    flash('Transaction approved.', 'success')
    return redirect(request.referrer or url_for('admin.transactions'))


@admin_bp.route("/transactions/<int:tx_id>/reject")
@login_required
@admin_required
def reject_transaction(tx_id):
    tx = db.session.get(Transaction, tx_id)
    if not tx:
        flash("Transaction not found.", "danger")
        return redirect(url_for("admin.transactions"))

    if tx.status != "pending":
        flash("Only pending transactions can be rejected.", "warning")
        return redirect(request.referrer or url_for("admin.transactions"))

    tx.status = "rejected"
    if tx.tx_type == "withdrawal":
        tx.user.usd_balance += tx.amount

    db.session.commit()
    flash("Transaction rejected.", "success")
    return redirect(request.referrer or url_for("admin.transactions"))


@admin_bp.route("/plans", methods=["GET", "POST"])
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
        flash("Plan created successfully.", "success")
        return redirect(url_for("admin.plans"))

    plans = InvestmentPlan.query.order_by(InvestmentPlan.created_at.desc()).all()
    return render_template("admin/plans.html", form=form, plans=plans)


@admin_bp.route("/plans/<int:plan_id>/toggle")
@login_required
@admin_required
def toggle_plan(plan_id):
    plan = db.session.get(InvestmentPlan, plan_id)
    if not plan:
        flash("Plan not found.", "danger")
        return redirect(url_for("admin.plans"))

    plan.is_active = not plan.is_active
    db.session.commit()
    flash("Plan visibility updated.", "success")
    return redirect(url_for("admin.plans"))


@admin_bp.route("/support", methods=["GET", "POST"])
@login_required
@admin_required
def support():
    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()

    if request.method == "POST":
        ticket_id = int(request.form.get("ticket_id"))
        reply = request.form.get("reply", "").strip()

        ticket = db.session.get(SupportTicket, ticket_id)
        if not ticket:
            flash("Ticket not found.", "danger")
            return redirect(url_for("admin.support"))

        ticket.admin_reply = reply
        if reply:
            ticket.status = "answered"
        db.session.commit()
        flash("Ticket updated.", "success")
        return redirect(url_for("admin.support"))

    return render_template("admin/support.html", tickets=tickets)


@admin_bp.route("/kyc")
@login_required
@admin_required
def kyc():
    return render_template("admin/placeholder.html", title="KYC Review", body="Connect your KYC provider and review documents here.")


@admin_bp.route("/content")
@login_required
@admin_required
def content():
    return render_template("admin/placeholder.html", title="Content Management", body="Manage homepage copy, FAQs, banners, and legal text here.")


@admin_bp.route("/reports")
@login_required
@admin_required
def reports():
    return render_template("admin/placeholder.html", title="Reports", body="Add CSV/PDF reporting for users, transactions, and revenue.")


@admin_bp.route("/notifications")
@login_required
@admin_required
def notifications():
    return render_template("admin/placeholder.html", title="Notifications", body="Send in-app or email broadcasts from here.")


@admin_bp.route("/settings")
@login_required
@admin_required
def settings():
    return render_template("admin/placeholder.html", title="System Settings", body="Store branding, SMTP, API keys, limits, and maintenance mode here.")


@admin_bp.route("/audit-logs")
@login_required
@admin_required
def audit_logs():
    return render_template("admin/placeholder.html", title="Audit Logs", body="Add persistent admin action logs before production launch.")


@admin_bp.route("/roles")
@login_required
@admin_required
def roles():
    return render_template("admin/placeholder.html", title="Roles & Permissions", body="Expand into granular RBAC for support, finance, and editors.")