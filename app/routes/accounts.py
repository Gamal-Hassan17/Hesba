from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from app import db
from app.models import FinancialAccount, Expense, FundingTransaction
from app.utils import login_required, parse_amount

accounts_bp = Blueprint("accounts", __name__)

def get_account(account_id):
    account = FinancialAccount.query.filter_by(
        id=account_id,
        user_id=session["user_id"]
    ).first()
    if not account:
        abort(404)
    return account

@accounts_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        is_budgeted = request.form.get("is_budgeted") == "yes"
        try:
            amount = parse_amount(request.form.get("initial_amount", "")) if is_budgeted else 0
            if not name:
                raise ValueError("اسم البند مطلوب.")
            if len(name) > 120 or len(description) > 500:
                raise ValueError("تجاوز أحد الحقول الحد المسموح به.")
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("add_account.html")
        account = FinancialAccount(
            user_id=session["user_id"],
            name=name,
            description=description,
            initial_amount=amount,
            is_budgeted=is_budgeted
        )
        db.session.add(account)
        db.session.commit()
        flash("تمت إضافة البند المالي بنجاح.", "success")
        return redirect(url_for("accounts.detail", account_id=account.id))
    return render_template("add_account.html")

@accounts_bp.route("/<int:account_id>")
@login_required
def detail(account_id):
    account = get_account(account_id)
    recent_expenses = Expense.query.filter_by(account_id=account.id).order_by(Expense.expense_date.desc()).limit(8).all()
    return render_template("account_details.html", account=account, recent_expenses=recent_expenses)

@accounts_bp.route("/<int:account_id>/edit", methods=["GET", "POST"])
@login_required
def edit(account_id):
    account = get_account(account_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name or len(name) > 120 or len(description) > 500:
            flash("تأكد من إدخال اسم صحيح ووصف لا يتجاوز 500 حرف.", "danger")
        else:
            account.name = name
            account.description = description
            db.session.commit()
            flash("تم تعديل بيانات البند.", "success")
            return redirect(url_for("accounts.detail", account_id=account.id))
    return render_template("edit_account.html", account=account)

@accounts_bp.route("/<int:account_id>/archive", methods=["POST"])
@login_required
def archive(account_id):
    account = get_account(account_id)
    account.is_archived = True
    db.session.commit()
    flash("تم أرشفة البند مع الاحتفاظ بسجلاته المالية.", "success")
    return redirect(url_for("dashboard.index"))
