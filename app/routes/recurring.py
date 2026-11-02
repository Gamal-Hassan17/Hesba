import calendar
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from app import db
from app.models import FinancialAccount, RecurringExpense, Expense
from app.utils import login_required, parse_amount, parse_datetime

recurring_bp = Blueprint("recurring", __name__)
FREQUENCIES = {"weekly": "أسبوعي", "monthly": "شهري", "yearly": "سنوي"}


def advance_date(value, frequency):
    if frequency == "weekly":
        return value + timedelta(days=7)
    months = 1 if frequency == "monthly" else 12
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def process_due_recurring(now=None, user_id=None):
    """Process only the current user's recurring rules (or all for trusted CLI use)."""
    now = now or datetime.now()
    query = RecurringExpense.query.join(
        FinancialAccount, RecurringExpense.account_id == FinancialAccount.id
    ).filter(RecurringExpense.is_active.is_(True))
    if user_id is not None:
        query = query.filter(FinancialAccount.user_id == user_id)

    rules = query.all()
    for rule in rules:
        account = rule.account
        if not account or account.is_archived:
            rule.is_active = False
            continue

        safety_count = 0
        while (
            rule.next_due <= now
            and (rule.end_date is None or rule.next_due.date() <= rule.end_date.date())
            and safety_count < 120
        ):
            db.session.add(Expense(
                account_id=rule.account_id,
                amount=rule.amount,
                description=f"{rule.description} (مصروف متكرر)",
                expense_date=rule.next_due,
            ))
            rule.next_due = advance_date(rule.next_due, rule.frequency)
            safety_count += 1

        if rule.end_date and rule.next_due.date() > rule.end_date.date():
            rule.is_active = False

    db.session.commit()


def get_rule(rule_id):
    rule = RecurringExpense.query.join(FinancialAccount).filter(
        RecurringExpense.id == rule_id,
        FinancialAccount.user_id == session["user_id"]
    ).first()
    if not rule:
        abort(404)
    return rule


@recurring_bp.route("/recurring", methods=["GET", "POST"])
@login_required
def index():
    process_due_recurring(user_id=session["user_id"])

    accounts = FinancialAccount.query.filter_by(
        user_id=session["user_id"], is_archived=False
    ).order_by(FinancialAccount.name.asc()).all()

    if request.method == "POST":
        try:
            account_id = int(request.form.get("account_id", ""))
            account = FinancialAccount.query.filter_by(
                id=account_id, user_id=session["user_id"]
            ).first()
            if not account or account.is_archived:
                raise ValueError("اختار بندًا ماليًا صالحًا.")
            description = request.form.get("description", "").strip()
            if not description or len(description) > 500:
                raise ValueError("وصف المصروف مطلوب ولا يتجاوز 500 حرف.")
            amount = parse_amount(request.form.get("amount", ""))
            frequency = request.form.get("frequency", "monthly")
            if frequency not in FREQUENCIES:
                raise ValueError("اختار معدل تكرار صحيحًا.")
            next_due = parse_datetime(request.form.get("next_due", ""))
            end_raw = request.form.get("end_date", "").strip()
            end_date = parse_datetime(end_raw + "T23:59") if end_raw else None
            if end_date and end_date < next_due:
                raise ValueError("تاريخ النهاية يجب أن يكون بعد تاريخ أول استحقاق.")
        except (ValueError, TypeError) as exc:
            flash(str(exc) or "راجع البيانات المدخلة.", "danger")
            return redirect(url_for("recurring.index"))

        db.session.add(RecurringExpense(
            account_id=account.id,
            amount=amount,
            description=description,
            frequency=frequency,
            next_due=next_due,
            end_date=end_date
        ))
        db.session.commit()
        flash("تم حفظ المصروف المتكرر. سيُسجَّل تلقائيًا عند موعد استحقاقه.", "success")
        return redirect(url_for("recurring.index"))

    rules = RecurringExpense.query.join(FinancialAccount).filter(
        FinancialAccount.user_id == session["user_id"]
    ).order_by(RecurringExpense.is_active.desc(), RecurringExpense.next_due.asc()).all()

    return render_template(
        "recurring.html", accounts=accounts, rules=rules, frequencies=FREQUENCIES
    )


@recurring_bp.route("/recurring/<int:rule_id>/toggle", methods=["POST"])
@login_required
def toggle(rule_id):
    rule = get_rule(rule_id)
    rule.is_active = not rule.is_active
    db.session.commit()
    flash("تم تحديث حالة المصروف المتكرر.", "success")
    return redirect(url_for("recurring.index"))


@recurring_bp.route("/recurring/<int:rule_id>/delete", methods=["POST"])
@login_required
def delete(rule_id):
    rule = get_rule(rule_id)
    db.session.delete(rule)
    db.session.commit()
    flash("تم حذف قاعدة المصروف المتكرر.", "success")
    return redirect(url_for("recurring.index"))
