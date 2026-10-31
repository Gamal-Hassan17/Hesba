from functools import wraps
from flask import session, redirect, url_for, request, flash
from decimal import Decimal, InvalidOperation
from datetime import datetime

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("سجّل الدخول أولًا للمتابعة.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def parse_amount(value):
    try:
        amount = Decimal((value or "").strip().replace(",", ""))
    except (InvalidOperation, AttributeError):
        raise ValueError("أدخل مبلغًا صحيحًا.")
    if not amount.is_finite() or amount <= 0 or amount > Decimal("999999999999.99"):
        raise ValueError("يجب أن يكون المبلغ أكبر من صفر وضمن النطاق المسموح.")
    return amount.quantize(Decimal("0.01"))

def parse_datetime(value):
    if not value:
        return datetime.now()
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("صيغة التاريخ أو الوقت غير صحيحة.")
