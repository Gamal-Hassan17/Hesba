import os
import click
from app import create_app, db
from app.models import User

app = create_app()

@app.cli.command("init-db")
def init_db():
    """Create database tables."""
    db.create_all()
    click.echo("تم إنشاء جداول قاعدة البيانات بنجاح.")

@app.cli.command("create-admin")
@click.option("--username", prompt="اسم المستخدم")
@click.option("--password", prompt="كلمة المرور", hide_input=True, confirmation_prompt=True)
def create_admin(username, password):
    """Create an additional user account."""
    db.create_all()
    if User.query.filter_by(username=username).first():
        click.echo("اسم المستخدم موجود بالفعل.")
        raise click.Abort()
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo("تم إنشاء حساب المستخدم بنجاح.")

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1"
    )
