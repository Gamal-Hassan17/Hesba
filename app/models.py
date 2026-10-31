from datetime import datetime
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FinancialAccount(db.Model):
    __tablename__ = "financial_accounts"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), default="", nullable=False)
    # is_budgeted=False means this is an expense-only tracker with no predefined budget.
    initial_amount = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    is_budgeted = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    expenses = db.relationship("Expense", backref="account", lazy=True, cascade="all, delete-orphan")
    funding_transactions = db.relationship("FundingTransaction", backref="account", lazy=True, cascade="all, delete-orphan")

    @property
    def total_funding(self):
        if not self.is_budgeted:
            return Decimal("0.00")
        return Decimal(self.initial_amount or 0) + sum(
            (Decimal(x.amount) for x in self.funding_transactions), Decimal("0.00")
        )

    @property
    def total_expenses(self):
        return sum((Decimal(x.amount) for x in self.expenses), Decimal("0.00"))

    @property
    def remaining_balance(self):
        if not self.is_budgeted:
            return None
        return self.total_funding - self.total_expenses

class FundingTransaction(db.Model):
    __tablename__ = "funding_transactions"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("financial_accounts.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    description = db.Column(db.String(500), default="", nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.now, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("financial_accounts.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    expense_date = db.Column(db.DateTime, default=datetime.now, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    receipt_path = db.Column(db.String(255), nullable=True)

class RecurringExpense(db.Model):
    __tablename__ = "recurring_expenses"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("financial_accounts.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    frequency = db.Column(db.String(20), nullable=False, default="monthly")
    next_due = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    account = db.relationship("FinancialAccount", backref=db.backref("recurring_expenses", lazy=True, cascade="all, delete-orphan"))
