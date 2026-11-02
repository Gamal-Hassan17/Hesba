from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from sqlalchemy.exc import IntegrityError

from app.models import User, FinancialAccount
from app import db
from app.utils import login_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            flash("أهلًا بك، تم تسجيل الدخول بنجاح.", "success")
            return redirect(url_for("dashboard.index"))

        flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "danger")

    return render_template("login.html", registration_closed=False)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3 or len(username) > 80:
            flash("اسم المستخدم يجب أن يكون من 3 إلى 80 حرفًا.", "danger")
        elif len(password) < 8:
            flash("كلمة المرور يجب أن تكون 8 أحرف على الأقل.", "danger")
        elif password != confirm_password:
            flash("كلمتا المرور غير متطابقتين.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("اسم المستخدم مستخدم بالفعل.", "danger")
        else:
            user = User(username=username)
            user.set_password(password)

            try:
                db.session.add(user)
                db.session.flush()

                # Claim any legacy accounts that existed before multi-user support.
                FinancialAccount.query.filter(
                    FinancialAccount.user_id.is_(None)
                ).update(
                    {FinancialAccount.user_id: user.id},
                    synchronize_session=False
                )

                db.session.commit()
                session.clear()
                session["user_id"] = user.id
                session["username"] = user.username
                flash("تم إنشاء حسابك بنجاح.", "success")
                return redirect(url_for("dashboard.index"))

            except IntegrityError:
                db.session.rollback()
                flash("اسم المستخدم مستخدم بالفعل. اختر اسمًا آخر.", "danger")

    return render_template("register.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("تم تسجيل الخروج.", "info")
    return redirect(url_for("auth.login"))
