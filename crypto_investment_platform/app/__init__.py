from flask import Flask
from .config import Config
from .extensions import db, login_manager, csrf, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    from .main.routes import main_bp
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    from .admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)

    from .models import User, InvestmentPlan

    @app.cli.command('init-db')
    def init_db():
        db.create_all()
        print('Database initialized.')

    @app.cli.command('seed-demo')
    def seed_demo():
        from werkzeug.security import generate_password_hash
        from .models import User, InvestmentPlan

        db.create_all()

        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                name='Admin User',
                email='admin@example.com',
                password_hash=generate_password_hash('Admin123!'),
                is_admin=True,
                usd_balance=0,
            )
            db.session.add(admin)

        if InvestmentPlan.query.count() == 0:
            plans = [
                InvestmentPlan(
                    name='Starter Plan',
                    description='Entry level diversified crypto exposure.',
                    min_amount=100,
                    duration_days=30,
                    target_return_percent=6.0,
                    risk_level='Medium'
                ),
                InvestmentPlan(
                    name='Growth Plan',
                    description='Longer duration allocation with broader market exposure.',
                    min_amount=500,
                    duration_days=90,
                    target_return_percent=18.0,
                    risk_level='High'
                ),
                InvestmentPlan(
                    name='Stable Yield Plan',
                    description='Conservative strategy focusing on lower-volatility assets.',
                    min_amount=250,
                    duration_days=60,
                    target_return_percent=9.0,
                    risk_level='Low'
                )
            ]
            db.session.add_all(plans)

        db.session.commit()
        print('Demo data seeded. Admin: admin@example.com / Admin123!')

    return app
