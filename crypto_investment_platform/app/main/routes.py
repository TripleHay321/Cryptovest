from flask import Blueprint, render_template
from ..models import InvestmentPlan

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    plans = InvestmentPlan.query.filter_by(is_active=True).limit(3).all()
    return render_template('main/index.html', plans=plans)


@main_bp.route('/about')
def about():
    return render_template('main/about.html')


@main_bp.route('/how-it-works')
def how_it_works():
    return render_template('main/how_it_works.html')


@main_bp.route('/plans')
def plans():
    plans = InvestmentPlan.query.filter_by(is_active=True).all()
    return render_template('main/plans.html', plans=plans)


@main_bp.route('/security')
def security():
    return render_template('main/security.html')


@main_bp.route('/fees')
def fees():
    return render_template('main/fees.html')


@main_bp.route('/faq')
def faq():
    return render_template('main/faq.html')


@main_bp.route('/contact')
def contact():
    return render_template('main/contact.html')


@main_bp.route('/terms')
def terms():
    return render_template('main/legal/terms.html')


@main_bp.route('/privacy')
def privacy():
    return render_template('main/legal/privacy.html')


@main_bp.route('/risk-disclosure')
def risk_disclosure():
    return render_template('main/legal/risk_disclosure.html')


@main_bp.route('/aml-kyc')
def aml_kyc():
    return render_template('main/legal/aml_kyc.html')


@main_bp.route('/cookies')
def cookies():
    return render_template('main/legal/cookies.html')


@main_bp.route('/compliance')
def compliance():
    return render_template('main/legal/compliance.html')
