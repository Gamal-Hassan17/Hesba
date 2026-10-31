"""Receipt storage with Supabase Storage in production and local fallback in development."""
from pathlib import Path
from urllib.parse import quote
import mimetypes
import requests
from flask import current_app

SUPABASE_PREFIX = "supabase:"


def _settings():
    url = current_app.config.get("SUPABASE_URL", "").rstrip("/")
    key = current_app.config.get("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = current_app.config.get("SUPABASE_BUCKET", "receipts")
    if not url and not key:
        return None
    if not url or not key:
        raise RuntimeError("يجب ضبط SUPABASE_URL وSUPABASE_SERVICE_ROLE_KEY معًا.")
    return url, key, bucket


def is_remote_receipt(receipt_path):
    return bool(receipt_path and receipt_path.startswith(SUPABASE_PREFIX))


def upload_receipt(file_storage, stored_name):
    settings = _settings()
    if not settings:
        folder = Path(current_app.instance_path) / "receipts"
        folder.mkdir(parents=True, exist_ok=True)
        file_storage.save(folder / stored_name)
        return stored_name

    url, key, bucket = settings
    object_path = stored_name
    content_type = file_storage.mimetype or mimetypes.guess_type(stored_name)[0] or "application/octet-stream"
    endpoint = f"{url}/storage/v1/object/{quote(bucket, safe='')}/{quote(object_path, safe='/')}"
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {key}", "apikey": key,
                 "Content-Type": content_type, "x-upsert": "false"},
        data=file_storage.read(), timeout=30,
    )
    response.raise_for_status()
    return SUPABASE_PREFIX + object_path


def receipt_view_url(receipt_path, expires_in=300):
    if not is_remote_receipt(receipt_path):
        return None
    settings = _settings()
    if not settings:
        raise RuntimeError("إعدادات Supabase Storage غير مكتملة.")
    url, key, bucket = settings
    object_path = receipt_path[len(SUPABASE_PREFIX):]
    endpoint = f"{url}/storage/v1/object/sign/{quote(bucket, safe='')}/{quote(object_path, safe='/')}"
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {key}", "apikey": key,
         "Content-Type": "application/json"},
        json={"expiresIn": expires_in}, timeout=20,
    )
    response.raise_for_status()
    signed_path = response.json().get("signedURL")
    if not signed_path:
        raise RuntimeError("لم يتمكن Supabase من إنشاء رابط عرض الإيصال.")
    if signed_path.startswith("http://") or signed_path.startswith("https://"):
        return signed_path
    return url + (signed_path if signed_path.startswith("/") else "/" + signed_path)


def delete_receipt(receipt_path):
    if not receipt_path:
        return
    if not is_remote_receipt(receipt_path):
        (Path(current_app.instance_path) / "receipts" / receipt_path).unlink(missing_ok=True)
        return
    settings = _settings()
    if not settings:
        current_app.logger.warning("Supabase is not configured; remote receipt was not deleted.")
        return
    url, key, bucket = settings
    object_path = receipt_path[len(SUPABASE_PREFIX):]
    endpoint = f"{url}/storage/v1/object/{quote(bucket, safe='')}/{quote(object_path, safe='/')}"
    response = requests.delete(endpoint, headers={"Authorization": f"Bearer {key}", "apikey": key}, timeout=20)
    response.raise_for_status()
