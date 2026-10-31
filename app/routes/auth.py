from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User
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
    return render_template("login.html", registration_closed=(User.query.count() > 0))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # First-run setup only: the first account becomes the owner/admin.
    if User.query.count() > 0:
        flash("تم إعداد حساب النظام بالفعل. إنشاء الحسابات الإضافية غير متاح من هذه الصفحة.", "info")
        return redirect(url_for("auth.login"))
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if len(username) < 3:
            flash("اسم المستخدم يجب أن يكون 3 أحرف على الأقل.", "danger")
        elif len(password) < 8:
            flash("كلمة المرور يجب أن تكون 8 أحرف على الأقل.", "danger")
        elif password != confirm_password:
            flash("كلمتا المرور غير متطابقتين.", "danger")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            flash("تم إنشاء حساب المدير بنجاح.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("register.html")

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("تم تسجيل الخروج.", "info")
    return redirect(url_for("auth.login"))
