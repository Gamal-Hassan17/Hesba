
from flask import Blueprint, render_template, session
from app.models import FinancialAccount
from app.routes.recurring import process_due_recurring
from app.utils import login_required
from decimal import Decimal

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():

    process_due_recurring(user_id=session["user_id"])
    accounts = FinancialAccount.query.filter_by(
        user_id=session["user_id"],
        is_archived=False
    ).order_by(FinancialAccount.created_at.desc()).all()

    # تقسيم الحسابات
    budgeted_accounts = [
        account for account in accounts
        if account.is_budgeted
    ]

    unbudgeted_accounts = [
        account for account in accounts
        if not account.is_budgeted
    ]

    # إجمالي الأموال المضافة للحسابات ذات الميزانية
    total_funding = sum(
        (account.total_funding for account in budgeted_accounts),
        Decimal("0.00")
    )

    # إجمالي المصروفات ببند
    budgeted_expenses = sum(
        (account.total_expenses for account in budgeted_accounts),
        Decimal("0.00")
    )

    # إجمالي المصروفات بدون بند
    unbudgeted_expenses = sum(
        (account.total_expenses for account in unbudgeted_accounts),
        Decimal("0.00")
    )

    # إجمالي المصروفات الكلية
    total_expenses = budgeted_expenses + unbudgeted_expenses

    # إجمالي المتبقي للحسابات ذات الميزانية
    total_remaining = sum(
        (account.remaining_balance for account in budgeted_accounts),
        Decimal("0.00")
    )

    return render_template(
        "dashboard.html",
        accounts=accounts,
        budgeted_accounts=budgeted_accounts,
        unbudgeted_accounts=unbudgeted_accounts,
        total_funding=total_funding,
        budgeted_expenses=budgeted_expenses,
        unbudgeted_expenses=unbudgeted_expenses,
        total_expenses=total_expenses,
        total_remaining=total_remaining
    )
