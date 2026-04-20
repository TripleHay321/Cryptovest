# Crypto Investment Platform (Flask Starter)

A multi-page Flask starter project for a crypto investment website with:
- public landing pages
- authentication
- user dashboard
- admin dashboard
- PostgreSQL-ready configuration
- role-based admin protection

## Important
This is a **starter/MVP codebase**, not a production-certified financial platform.
Before real deployment you must add:
- legal review
- KYC/AML provider integration
- payment/wallet provider integration
- security hardening
- transaction signing controls
- audit logging
- monitoring and backups

## Quick start

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env
python run.py
```

## Database setup
Open Flask shell or use `flask shell`, then:

```python
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    db.create_all()
```

Or use the provided CLI command:

```bash
flask init-db
flask seed-demo
```

## Demo admin
After `flask seed-demo`:
- admin email: `admin@example.com`
- password: `Admin123!`

## Environment variables
- `SECRET_KEY`
- `DATABASE_URL` (use PostgreSQL in production)
