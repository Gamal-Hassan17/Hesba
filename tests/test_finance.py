from decimal import Decimal
from app import db
from app.models import User, FinancialAccount, Expense, FundingTransaction

def make_user(username="test-user"):
    user = User(username=username)
    user.set_password("test-password")
    db.session.add(user)
    db.session.flush()
    return user


def test_account_totals(app):
    with app.app_context():
        user = make_user()
        account = FinancialAccount(user_id=user.id, name="فلوس البيت", description="", initial_amount=Decimal("1000.00"))
        db.session.add(account)
        db.session.flush()
        db.session.add(Expense(account_id=account.id, amount=Decimal("125.00"), description="أكل"))
        db.session.add(FundingTransaction(account_id=account.id, amount=Decimal("50.00"), description="إضافة"))
        db.session.commit()
        db.session.refresh(account)
        assert account.total_funding == Decimal("1050.00")
        assert account.total_expenses == Decimal("125.00")
        assert account.remaining_balance == Decimal("925.00")

def test_expenses_are_account_specific(app):
    with app.app_context():
        user = make_user()
        a = FinancialAccount(user_id=user.id, name="أ", initial_amount=Decimal("1000.00"))
        b = FinancialAccount(user_id=user.id, name="ب", initial_amount=Decimal("2000.00"))
        db.session.add_all([a, b])
        db.session.flush()
        db.session.add(Expense(account_id=a.id, amount=Decimal("100.00"), description="مصروف أ"))
        db.session.commit()
        assert a.total_expenses == Decimal("100.00")
        assert b.total_expenses == Decimal("0.00")


def test_recurring_expense_generates_due_entries_and_advances_schedule(app):
    from datetime import datetime, timedelta
    from app.models import RecurringExpense
    from app.routes.recurring import process_due_recurring
    with app.app_context():
        user = make_user()
        account = FinancialAccount(user_id=user.id, name="فواتير", initial_amount=1000)
        db.session.add(account)
        db.session.flush()
        due = datetime.now() - timedelta(days=2)
        rule = RecurringExpense(account_id=account.id, amount=Decimal("120.00"),
                                description="فاتورة الإنترنت", frequency="monthly", next_due=due)
        db.session.add(rule)
        db.session.commit()
        process_due_recurring()
        assert Expense.query.filter_by(account_id=account.id).count() == 1
        db.session.refresh(rule)
        assert rule.next_due > due


def test_users_can_register_independently_and_accounts_are_isolated(client, app):
    response = client.post("/register", data={
        "username": "alice",
        "password": "password123",
        "confirm_password": "password123",
    }, follow_redirects=True)
    assert response.status_code == 200

    with client.session_transaction() as sess:
        alice_id = sess["user_id"]

    with app.app_context():
        alice_account = FinancialAccount(
            user_id=alice_id, name="حساب أليس", initial_amount=100
        )
        db.session.add(alice_account)
        db.session.commit()
        alice_account_id = alice_account.id

    client.post("/logout", follow_redirects=True)
    response = client.post("/register", data={
        "username": "bob",
        "password": "password123",
        "confirm_password": "password123",
    }, follow_redirects=True)
    assert response.status_code == 200

    with client.session_transaction() as sess:
        bob_id = sess["user_id"]
        assert bob_id != alice_id

    response = client.get(f"/accounts/{alice_account_id}")
    assert response.status_code == 404

    with app.app_context():
        assert FinancialAccount.query.filter_by(user_id=bob_id).count() == 0
        assert FinancialAccount.query.filter_by(user_id=alice_id).count() == 1
