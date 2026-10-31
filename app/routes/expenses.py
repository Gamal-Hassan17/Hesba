from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from uuid import uuid4
from werkzeug.utils import secure_filename
from app import db
from app.models import Expense, FinancialAccount
from app.utils import login_required, parse_amount, parse_datetime
from app.services.receipt_storage import upload_receipt, delete_receipt
import requests

expenses_bp = Blueprint("expenses", __name__)
ALLOWED_RECEIPT_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf"}

def save_receipt(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    safe_name = secure_filename(file_storage.filename)
    extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if extension not in ALLOWED_RECEIPT_EXTENSIONS:
        raise ValueError("صيغة الإيصال غير مدعومة. استخدم JPG أو PNG أو WEBP أو PDF.")
    stored_name = f"{uuid4().hex}.{extension}"
    try:
        return upload_receipt(file_storage, stored_name)
    except requests.RequestException as exc:
        current_app.logger.exception("Receipt upload failed")
        raise ValueError("تعذر رفع الإيصال إلى التخزين السحابي. تحقق من إعدادات Supabase وحاول مرة أخرى.") from exc
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc

def get_account(account_id):
    account = db.session.get(FinancialAccount, account_id)
    if not account:
        abort(404)
    if account.is_archived:
        abort(400, description="لا يمكن إضافة مصروف إلى بند مؤرشف.")
    return account

def get_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if not expense:
        abort(404)
    return expense

@expenses_bp.route("/account/<int:account_id>")
@login_required
def list_for_account(account_id):
    account = db.session.get(FinancialAccount, account_id)
    if not account:
        abort(404)
    query = Expense.query.filter_by(account_id=account.id)
    search = request.args.get("q", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    sort = request.args.get("sort", "newest")
    if search:
        query = query.filter(Expense.description.ilike(f"%{search}%"))
    if date_from:
        try:
            query = query.filter(Expense.expense_date >= parse_datetime(date_from + "T00:00"))
        except ValueError:
            flash("تاريخ البداية غير صحيح.", "warning")
    if date_to:
        try:
            query = query.filter(Expense.expense_date <= parse_datetime(date_to + "T23:59:59"))
        except ValueError:
            flash("تاريخ النهاية غير صحيح.", "warning")
    if sort == "oldest":
        query = query.order_by(Expense.expense_date.asc())
    elif sort == "amount_high":
        query = query.order_by(Expense.amount.desc())
    elif sort == "amount_low":
        query = query.order_by(Expense.amount.asc())
    else:
        query = query.order_by(Expense.expense_date.desc())
    expenses = query.all()
    filtered_total = sum((e.amount for e in expenses), start=0)
    return render_template("expenses.html", account=account, expenses=expenses,
                           filtered_total=filtered_total, search=search,
                           date_from=date_from, date_to=date_to, sort=sort)

@expenses_bp.route("/account/<int:account_id>/new", methods=["GET", "POST"])
@login_required
def create(account_id):
    account = get_account(account_id)
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        try:
            amount = parse_amount(request.form.get("amount", ""))
            expense_date = parse_datetime(request.form.get("expense_date", ""))
            if not description:
                raise ValueError("وصف المصروف مطلوب.")
            if len(description) > 500:
                raise ValueError("وصف المصروف يجب ألا يتجاوز 500 حرف.")
            receipt_path = save_receipt(request.files.get("receipt"))
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("add_expense.html", account=account)
        expense = Expense(account_id=account.id, amount=amount, description=description, expense_date=expense_date, receipt_path=receipt_path)
        db.session.add(expense)
        db.session.commit()
        flash("تم حفظ المصروف وتحديث الرصيد.", "success")
        return redirect(url_for("expenses.list_for_account", account_id=account.id))
    return render_template("add_expense.html", account=account)

@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    expense = get_expense(expense_id)
    if expense.account.is_archived:
        abort(400, description="لا يمكن تعديل مصروف في بند مؤرشف.")
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        try:
            amount = parse_amount(request.form.get("amount", ""))
            expense_date = parse_datetime(request.form.get("expense_date", ""))
            if not description:
                raise ValueError("وصف المصروف مطلوب.")
            if len(description) > 500:
                raise ValueError("وصف المصروف يجب ألا يتجاوز 500 حرف.")
            new_receipt = save_receipt(request.files.get("receipt"))
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("edit_expense.html", expense=expense)
        if new_receipt:
            if expense.receipt_path:
                try:
                    delete_receipt(expense.receipt_path)
                except requests.RequestException:
                    current_app.logger.exception("Old receipt cleanup failed")
            expense.receipt_path = new_receipt
        expense.amount = amount
        expense.description = description
        expense.expense_date = expense_date
        db.session.commit()
        flash("تم تعديل المصروف وتحديث الإجمالي.", "success")
        return redirect(url_for("expenses.list_for_account", account_id=expense.account_id))
    return render_template("edit_expense.html", expense=expense)

@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id):
    expense = get_expense(expense_id)
    account_id = expense.account_id
    if expense.account.is_archived:
        abort(400, description="لا يمكن حذف مصروف من بند مؤرشف.")
    if expense.receipt_path:
        try:
            delete_receipt(expense.receipt_path)
        except requests.RequestException:
            current_app.logger.exception("Receipt cleanup failed")
    db.session.delete(expense)
    db.session.commit()
    flash("تم حذف المصروف وتحديث الإجمالي.", "success")
    return redirect(url_for("expenses.list_for_account", account_id=account_id))
