from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    app.config["MAX_CONTENT_LENGTH"] = app.config.get("MAX_CONTENT_LENGTH") or 5 * 1024 * 1024

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)

    @app.template_filter("money")
    def money_filter(value):
        try:
            return f"{float(value):,.2f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            return "0"

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.accounts import accounts_bp
    from app.routes.expenses import expenses_bp
    from app.routes.funding import funding_bp
    from app.routes.backup import backup_bp
    from app.routes.analytics import analytics_bp
    from app.routes.recurring import recurring_bp
    from app.routes.receipts import receipts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounts_bp, url_prefix="/accounts")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(funding_bp, url_prefix="/funding")
    app.register_blueprint(backup_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(receipts_bp)

    with app.app_context():
        db.create_all()
        # Lightweight migration for databases created by earlier versions.
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if "financial_accounts" in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns("financial_accounts")}
            if "is_budgeted" not in columns:
                with db.engine.begin() as connection:
                    connection.execute(text("ALTER TABLE financial_accounts ADD COLUMN is_budgeted BOOLEAN NOT NULL DEFAULT TRUE"))
        if "expenses" in inspector.get_table_names():
            expense_columns = {column["name"] for column in inspector.get_columns("expenses")}
            if "receipt_path" not in expense_columns:
                with db.engine.begin() as connection:
                    connection.execute(text("ALTER TABLE expenses ADD COLUMN receipt_path VARCHAR(255)"))

    return app
