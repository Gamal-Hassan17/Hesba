from flask import Blueprint, request, jsonify, send_file, session
from io import BytesIO
from app.utils import login_required
from app.services.excel_backup import merge_workbook, FILENAME
from app import csrf

backup_bp = Blueprint("backup", __name__)

@backup_bp.route("/api/excel-backup/sync", methods=["POST"])
@login_required
@csrf.exempt
def sync_excel_backup():
    uploaded = request.files.get("workbook")
    try:
        data = merge_workbook(uploaded.read() if uploaded else None, session["user_id"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    response = send_file(BytesIO(data), as_attachment=True, download_name=FILENAME,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Cache-Control"] = "no-store"
    return response

@backup_bp.route("/api/excel-backup/account/<int:account_id>/sync", methods=["POST"])
@login_required
@csrf.exempt
def sync_account_excel_backup(account_id):
    from app.services.excel_backup import merge_account_workbook
    uploaded = request.files.get("workbook")
    try:
        data = merge_account_workbook(uploaded.read() if uploaded else None, session["user_id"], account_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    response = send_file(BytesIO(data), as_attachment=True,
                         download_name=f"Hesba_Band_{account_id}_Backup.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Cache-Control"] = "no-store"
    return response
