from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal
from flask import Blueprint, render_template, request
from sqlalchemy import func
from app import db
from app.models import Expense, FinancialAccount
from app.utils import login_required, parse_datetime

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/reports")
@login_required
def reports():
    today = datetime.now().date()
    default_start = today.replace(day=1)
    start_raw = request.args.get("from", default_start.isoformat())
    end_raw = request.args.get("to", today.isoformat())
    selected_id = request.args.get("account", type=int)
    try:
        start = parse_datetime(start_raw + "T00:00")
        end = parse_datetime(end_raw + "T23:59:59")
        if start > end:
            raise ValueError
    except ValueError:
        start = parse_datetime(default_start.isoformat() + "T00:00")
        end = parse_datetime(today.isoformat() + "T23:59:59")
        start_raw, end_raw = default_start.isoformat(), today.isoformat()

    accounts = FinancialAccount.query.filter_by(is_archived=False).order_by(FinancialAccount.name.asc()).all()
    selected_account = db.session.get(FinancialAccount, selected_id) if selected_id else None
    if selected_account and selected_account.is_archived:
        selected_account = None
        selected_id = None
    query = (db.session.query(Expense, FinancialAccount)
             .join(FinancialAccount, Expense.account_id == FinancialAccount.id)
             .filter(Expense.expense_date >= start, Expense.expense_date <= end))
    if selected_account:
        query = query.filter(FinancialAccount.id == selected_account.id)
    rows = query.order_by(Expense.expense_date.desc()).all()
    total = sum((Decimal(expense.amount) for expense, _ in rows), Decimal("0.00"))
    category_totals = defaultdict(lambda: Decimal("0.00"))
    description_totals = defaultdict(lambda: Decimal("0.00"))
    for expense, account in rows:
        category_totals[account.name] += Decimal(expense.amount)
        description_totals[expense.description or "مصروف بدون وصف"] += Decimal(expense.amount)
    categories = sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    descriptions = sorted(description_totals.items(), key=lambda item: item[1], reverse=True)[:8]
    previous_start = (start.replace(day=1) - timedelta(days=1)).replace(day=1)
    previous_end = start.replace(day=1) - timedelta(seconds=1)
    previous_query = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.expense_date >= previous_start, Expense.expense_date <= previous_end)
    if selected_account:
        previous_query = previous_query.filter(Expense.account_id == selected_account.id)
    previous_total = previous_query.scalar() or 0
    change_percent = None if not previous_total else float((total - Decimal(previous_total)) / Decimal(previous_total) * 100)

    budget_spent = Decimal("0.00")
    budget_total = Decimal("0.00")
    budget_remaining = Decimal("0.00")
    budget_percent = 0
    over_budget = Decimal("0.00")
    if selected_account and selected_account.is_budgeted:
        budget_total = Decimal(selected_account.total_funding)
        budget_spent = Decimal(selected_account.total_expenses)
        budget_remaining = max(Decimal("0.00"), budget_total - budget_spent)
        over_budget = max(Decimal("0.00"), budget_spent - budget_total)
        budget_percent = float(min(Decimal("100"), budget_spent / budget_total * 100)) if budget_total > 0 else (100 if budget_spent else 0)

    return render_template("reports.html", total=total, count=len(rows), categories=categories,
        descriptions=descriptions, start_date=start_raw, end_date=end_raw, previous_total=Decimal(previous_total),
        change_percent=change_percent, expenses=[e for e, _ in rows], accounts=accounts,
        selected_account=selected_account, selected_account_id=selected_id,
        budget_total=budget_total, budget_spent=budget_spent, budget_remaining=budget_remaining,
        budget_percent=budget_percent, over_budget=over_budget)
