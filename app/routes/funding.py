from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from app import db
from app.models import FinancialAccount, FundingTransaction
from app.utils import login_required, parse_amount, parse_datetime

funding_bp = Blueprint("funding", __name__)

@funding_bp.route("/account/<int:account_id>/new", methods=["GET", "POST"])
@login_required
def create(account_id):
    account = FinancialAccount.query.filter_by(
        id=account_id,
        user_id=session["user_id"]
    ).first()
    if not account:
        abort(404)
    if account.is_archived:
        abort(400, description="لا يمكن إضافة أموال إلى بند مؤرشف.")
    if not account.is_budgeted:
        flash("هذا البند مخصص لتسجيل المصروفات فقط ولا يحتاج إلى إضافة ميزانية.", "info")
        return redirect(url_for("accounts.detail", account_id=account.id))
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        try:
            amount = parse_amount(request.form.get("amount", ""))
            transaction_date = parse_datetime(request.form.get("transaction_date", ""))
            if len(description) > 500:
                raise ValueError("الوصف يجب ألا يتجاوز 500 حرف.")
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("add_funding.html", account=account)
        transaction = FundingTransaction(account_id=account.id, amount=amount,
                                         description=description, transaction_date=transaction_date)
        db.session.add(transaction)
        db.session.commit()
        flash("تمت إضافة المبلغ وتحديث الرصيد.", "success")
        return redirect(url_for("accounts.detail", account_id=account.id))
    return render_template("add_funding.html", account=account)
