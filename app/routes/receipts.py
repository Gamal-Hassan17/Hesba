from flask import Blueprint, abort, redirect, current_app, send_from_directory
from pathlib import Path
from app.models import Expense
from app.utils import login_required
from app.services.receipt_storage import receipt_view_url, is_remote_receipt
import requests

receipts_bp = Blueprint("receipts", __name__)

@receipts_bp.route("/receipts/<int:expense_id>")
@login_required
def view(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if not expense.receipt_path:
        abort(404)
    if is_remote_receipt(expense.receipt_path):
        try:
            return redirect(receipt_view_url(expense.receipt_path))
        except (requests.RequestException, RuntimeError):
            current_app.logger.exception("Could not create receipt signed URL")
            abort(503, description="تعذر فتح الإيصال حاليًا. حاول مرة أخرى لاحقًا.")
    root = Path(current_app.instance_path) / "receipts"
    return send_from_directory(root, expense.receipt_path, as_attachment=False, conditional=True)
