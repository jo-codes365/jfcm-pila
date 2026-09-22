import hashlib
import json
import logging
import os
import re
import secrets
import shutil
import smtplib
import subprocess
import tempfile
import uuid
import zipfile
import calendar as calendar_module
from urllib.parse import urlparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import BytesIO
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from flask_wtf.csrf import CSRFProtect
from mysql.connector import Error as MySQLError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


MAX_FILE_SIZE_MB = env_int("MAX_FILE_SIZE_MB", 50)
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
UPLOAD_REQUEST_OVERHEAD_BYTES = 1024 * 1024
TRASH_RETENTION_DAYS = 30
SESSION_INACTIVITY_DAYS = 7
SESSION_LAST_ACTIVITY_KEY = "last_activity_at"
OFFLINE_CACHE_SCOPE_KEY = "offline_cache_scope"
UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", "uploads"))
if not UPLOAD_FOLDER.is_absolute():
    UPLOAD_FOLDER = BASE_DIR / UPLOAD_FOLDER
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
PRESENTATION_PREVIEW_FOLDER = UPLOAD_FOLDER / ".presentation-previews"
PRESENTATION_PREVIEW_DPI = max(144, min(env_int("PRESENTATION_PREVIEW_DPI", 240), 360))
PRESENTATION_PREVIEW_RENDERER_VERSION = "animation-steps-v1"
PRESENTATION_PRE_RENDERED_FOLDER = Path(
    os.getenv("POWERPOINT_PRE_RENDERED_FOLDER", str(UPLOAD_FOLDER / ".powerpoint-prerendered"))
)
if not PRESENTATION_PRE_RENDERED_FOLDER.is_absolute():
    PRESENTATION_PRE_RENDERED_FOLDER = BASE_DIR / PRESENTATION_PRE_RENDERED_FOLDER

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "change-this-before-production"),
    MAX_CONTENT_LENGTH=MAX_FILE_SIZE_BYTES + UPLOAD_REQUEST_OVERHEAD_BYTES,
    UPLOAD_FOLDER=str(UPLOAD_FOLDER),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(days=SESSION_INACTIVITY_DAYS),
)
csrf = CSRFProtect(app)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO)

# SMTP Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = env_int("SMTP_PORT", 587)
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USERNAME)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "JFCM Pila")
PRIVACY_CONTACT_EMAIL = os.getenv("PRIVACY_CONTACT_EMAIL", "").strip()


def send_welcome_email(email, subject="Welcome to JFCM Pila"):
    """Send a welcome email to a new user."""
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM_EMAIL:
        app.logger.warning("SMTP not configured; welcome email not sent")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = email
        
        text = f"Welcome to JFCM Pila!\n\nYour account has been successfully created.\n\nYou can now sign in at the login page."
        html = f"""
        <html>
            <body>
            <h2>Welcome to JFCM Pila!</h2>
            <p>Your account has been successfully created.</p>
            <p>You can now sign in using your email and password.</p>
            <p style="margin-top: 30px; color: #999;">This is an automated message, please do not reply.</p>
            </body>
        </html>
        """
        
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        app.logger.exception(f"Failed to send welcome email to {email}")
        return False




def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(
            host=os.getenv("MYSQLHOST"),
            port=int(os.getenv("MYSQLPORT", 3306)),
            user=os.getenv("MYSQLUSER"),
            password=os.getenv("MYSQLPASSWORD"),
            database=os.getenv("MYSQLDATABASE"),
            autocommit=False,
            )
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None and db.is_connected():
        db.close()


def query_one(sql, values):
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(sql, values)
        return cursor.fetchone()
    finally:
        cursor.close()


def session_inactivity_deadline():
    return timedelta(days=SESSION_INACTIVITY_DAYS)


def touch_authenticated_session():
    session[SESSION_LAST_ACTIVITY_KEY] = datetime.now().isoformat()
    session.permanent = True
    session.modified = True


def current_offline_cache_scope():
    if "user_id" not in session:
        return "public"
    if not session.get(OFFLINE_CACHE_SCOPE_KEY):
        session[OFFLINE_CACHE_SCOPE_KEY] = secrets.token_urlsafe(24)
    return f"private:{session[OFFLINE_CACHE_SCOPE_KEY]}"


def session_is_expired():
    last_activity_raw = session.get(SESSION_LAST_ACTIVITY_KEY)
    if not last_activity_raw:
        return True
    try:
        last_activity = datetime.fromisoformat(last_activity_raw)
    except ValueError:
        return True
    return datetime.now() - last_activity > session_inactivity_deadline()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))
        if session_is_expired():
            session.clear()
            flash("Your session expired after 7 days of inactivity. Please sign in again.", "error")
            return redirect(url_for("login"))
        touch_authenticated_session()
        purge_expired_trash(session["user_id"])
        return view(*args, **kwargs)
    return wrapped


def login_or_public_link_required(view):
    """Allow an active signed-in session or a valid public-link context."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        share_context = request_share_context()
        if "user_id" not in session:
            if not share_context:
                flash("Please sign in to continue.", "error")
                return redirect(url_for("login"))
        elif session_is_expired():
            session.clear()
            if not share_context:
                flash("Your session expired after 7 days of inactivity. Please sign in again.", "error")
                return redirect(url_for("login"))
        else:
            touch_authenticated_session()
            purge_expired_trash(session["user_id"])
        return view(*args, **kwargs)
    return wrapped


def delete_physical_file(owner_id, stored_filename):
    path = UPLOAD_FOLDER / str(owner_id) / stored_filename
    if path.is_file():
        path.unlink()


def delete_presentation_previews(owner_id, file_id):
    owner_preview_directory = PRESENTATION_PREVIEW_FOLDER / str(int(owner_id))
    if not owner_preview_directory.is_dir():
        return
    for cache_directory in owner_preview_directory.glob(f"{int(file_id)}-*"):
        if cache_directory.is_dir() and cache_directory.parent == owner_preview_directory:
            shutil.rmtree(cache_directory)


def permanently_delete_file_record(cursor, record):
    delete_physical_file(record["user_id"], record["stored_filename"])
    delete_presentation_previews(record["user_id"], record["id"])
    cursor.execute("DELETE FROM files WHERE id = %s AND user_id = %s", (record["id"], record["user_id"]))


def permanently_delete_folder_record(cursor, folder):
    folder_ids = [folder["id"], *folder_descendants(folder["id"], owner_id=folder["user_id"], include_deleted=True)]
    placeholders = ",".join(["%s"] * len(folder_ids))
    cursor.execute(
        f"SELECT id, user_id, stored_filename FROM files WHERE user_id = %s AND folder_id IN ({placeholders})",
        (folder["user_id"], *folder_ids),
    )
    for record in cursor.fetchall():
        delete_physical_file(record["user_id"], record["stored_filename"])
        delete_presentation_previews(record["user_id"], record["id"])
    cursor.execute(f"DELETE FROM files WHERE user_id = %s AND folder_id IN ({placeholders})", (folder["user_id"], *folder_ids))
    cursor.execute(f"UPDATE folders SET parent_id = NULL WHERE user_id = %s AND id IN ({placeholders})", (folder["user_id"], *folder_ids))
    cursor.execute(f"DELETE FROM folders WHERE user_id = %s AND id IN ({placeholders})", (folder["user_id"], *folder_ids))


def permanently_delete_event_record(cursor, event):
    cursor.execute("SELECT id, user_id, stored_filename FROM files WHERE user_id = %s AND event_id = %s", (event["user_id"], event["id"]))
    for record in cursor.fetchall():
        delete_physical_file(record["user_id"], record["stored_filename"])
        delete_presentation_previews(record["user_id"], record["id"])
    cursor.execute("DELETE FROM files WHERE user_id = %s AND event_id = %s", (event["user_id"], event["id"]))
    cursor.execute("UPDATE folders SET parent_id = NULL WHERE user_id = %s AND event_id = %s", (event["user_id"], event["id"]))
    cursor.execute("DELETE FROM folders WHERE user_id = %s AND event_id = %s", (event["user_id"], event["id"]))
    cursor.execute("DELETE FROM events WHERE id = %s AND user_id = %s", (event["id"], event["user_id"]))


def purge_expired_trash(owner_id):
    cutoff = datetime.now() - timedelta(days=TRASH_RETENTION_DAYS)
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, user_id, name FROM events WHERE user_id = %s AND is_deleted = TRUE AND deleted_at <= %s", (owner_id, cutoff))
        for event in cursor.fetchall():
            permanently_delete_event_record(cursor, event)

        cursor.execute(
            "SELECT id, user_id, name FROM folders WHERE user_id = %s AND is_deleted = TRUE AND deleted_at <= %s ORDER BY id",
            (owner_id, cutoff),
        )
        deleted_folder_ids = set()
        for folder in cursor.fetchall():
            if folder["id"] in deleted_folder_ids:
                continue
            subtree_ids = [folder["id"], *folder_descendants(folder["id"], owner_id=folder["user_id"], include_deleted=True)]
            permanently_delete_folder_record(cursor, folder)
            deleted_folder_ids.update(subtree_ids)

        cursor.execute("SELECT id, user_id, stored_filename FROM files WHERE user_id = %s AND is_deleted = TRUE AND deleted_at <= %s", (owner_id, cutoff))
        for record in cursor.fetchall():
            permanently_delete_file_record(cursor, record)
        get_db().commit()
    except (MySQLError, OSError):
        get_db().rollback()
        app.logger.exception("Automatic trash expiration failed")
    finally:
        cursor.close()


def file_record(file_id, include_deleted=False):
    deleted_condition = "" if include_deleted else " AND files.is_deleted = FALSE"
    return query_one(
        "SELECT files.id, files.user_id, files.original_filename, files.stored_filename, files.file_size, files.mime_type, "
        "files.uploaded_at, files.accessed_at, files.share_token, "
        "files.folder_id, files.event_id, files.is_starred, users.username AS owner "
        "FROM files JOIN users ON users.id = files.user_id "
        "WHERE files.id = %s" + deleted_condition,
        (file_id,),
    )


def event_record(event_id, include_deleted=False):
    condition = "" if include_deleted else " AND is_deleted = FALSE"
    return query_one(
        "SELECT id, user_id, name, event_date, event_type, share_token, "
        "is_starred, is_deleted, created_at "
        "FROM events WHERE id = %s" + condition,
        (event_id,),
    )


def owned_file(file_id):
    record = file_record(file_id)
    if record and record["user_id"] == session["user_id"]:
        return record
    return None


def owned_folder(folder_id, include_deleted=False):
    condition = "" if include_deleted else " AND is_deleted = FALSE"
    return query_one(
        "SELECT id, user_id, parent_id, event_id, original_parent_id, name, share_token, "
        "is_starred, is_deleted "
        "FROM folders WHERE id = %s AND user_id = %s" + condition,
        (folder_id, session["user_id"]),
    )


def folder_record(folder_id, include_deleted=False):
    condition = "" if include_deleted else " AND is_deleted = FALSE"
    return query_one(
        "SELECT id, user_id, parent_id, event_id, original_parent_id, name, share_token, "
        "is_starred, is_deleted, created_at "
        "FROM folders WHERE id = %s" + condition,
        (folder_id,),
    )


def owned_event(event_id, include_deleted=False):
    record = event_record(event_id, include_deleted=include_deleted)
    if record and record["user_id"] == session["user_id"]:
        return record
    return None


def valid_event(event_id):
    if event_id in (None, ""):
        return None
    try:
        event_id = int(event_id)
    except (TypeError, ValueError):
        abort(400)
    if not owned_event(event_id):
        abort(404)
    return event_id


def valid_destination(folder_id):
    if folder_id in (None, "", "root"):
        return None
    try:
        folder_id = int(folder_id)
    except (TypeError, ValueError):
        abort(400)
    folder = owned_folder(folder_id)
    if not folder:
        abort(404)
    return folder_id


def event_archive_contents(event):
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, parent_id, name FROM folders WHERE user_id = %s AND event_id = %s AND is_deleted = FALSE ORDER BY id",
            (event["user_id"], event["id"]),
        )
        folders = cursor.fetchall()
        cursor.execute(
            "SELECT stored_filename, original_filename, folder_id FROM files WHERE user_id = %s AND event_id = %s AND is_deleted = FALSE ORDER BY id",
            (event["user_id"], event["id"]),
        )
        files = cursor.fetchall()
    finally:
        cursor.close()
    return folders, files


def write_event_archive(bundle, event, written_paths=None):
    folders, files = event_archive_contents(event)
    event_root = event["name"]
    if written_paths is not None:
        candidate_root = event_root
        counter = 2
        while f"{candidate_root}/" in written_paths:
            candidate_root = f"{event_root} ({counter})"
            counter += 1
        event_root = candidate_root
        written_paths.add(f"{event_root}/")
    bundle.writestr(f"{event_root}/", "")

    relative_paths = {}
    pending = [None]
    while pending:
        parent_id = pending.pop()
        for child in folders:
            if child["parent_id"] == parent_id:
                parent_path = event_root if parent_id is None else relative_paths[parent_id]
                relative_paths[child["id"]] = f"{parent_path}/{child['name']}"
                pending.append(child["id"])

    for folder in folders:
        folder_path = f"{relative_paths[folder['id']]}/"
        if written_paths is None or folder_path not in written_paths:
            if written_paths is not None:
                written_paths.add(folder_path)
            bundle.writestr(folder_path, "")

    owner_directory = user_directory(event["user_id"])
    for file_record in files:
        path = owner_directory / file_record["stored_filename"]
        if not path.is_file():
            continue
        parent_path = event_root if file_record["folder_id"] is None else relative_paths.get(file_record["folder_id"])
        if not parent_path:
            continue
        archive_path = f"{parent_path}/{file_record['original_filename']}"
        if written_paths is None:
            bundle.write(path, arcname=archive_path)
            continue
        candidate_path = archive_path
        counter = 2
        while candidate_path in written_paths:
            stem, suffix = os.path.splitext(archive_path)
            candidate_path = f"{stem} ({counter}){suffix}"
            counter += 1
        written_paths.add(candidate_path)
        bundle.write(path, arcname=candidate_path)


def user_directory(user_id):
    return UPLOAD_FOLDER / str(user_id)


def folder_chain(folder_id, stop_at=None):
    chain = []
    current_id = folder_id
    seen = set()
    while current_id and current_id not in seen:
        folder = folder_record(current_id)
        if not folder:
            break
        chain.append(folder)
        if stop_at and current_id == stop_at:
            break
        seen.add(current_id)
        current_id = folder["parent_id"]
    return chain


def folder_is_within(folder_id, root_folder_id):
    return any(folder["id"] == root_folder_id for folder in folder_chain(folder_id))


def share_context_from_token(kind, share_token):
    current_user_id = session.get("user_id")
    if kind == "file":
        record = query_one(
            "SELECT id, user_id, event_id, share_token "
            "FROM files WHERE share_token = %s AND is_deleted = FALSE",
            (share_token,),
        )
        if not record:
            return None
        return {
            "kind": "file",
            "token": share_token,
            "item_id": record["id"],
            "owner_id": record["user_id"],
            "can_edit": bool(current_user_id and record["user_id"] == current_user_id),
        }

    if kind == "event":
        record = query_one(
            "SELECT id, user_id, share_token "
            "FROM events WHERE share_token = %s AND is_deleted = FALSE",
            (share_token,),
        )
        if not record:
            return None
        return {
            "kind": "event",
            "token": share_token,
            "item_id": record["id"],
            "owner_id": record["user_id"],
            "can_edit": bool(current_user_id and record["user_id"] == current_user_id),
        }

    record = query_one(
        "SELECT id, user_id, share_token "
        "FROM folders WHERE share_token = %s AND is_deleted = FALSE",
        (share_token,),
    )
    if not record:
        return None
    return {
        "kind": "folder",
        "token": share_token,
        "item_id": record["id"],
        "owner_id": record["user_id"],
        "can_edit": bool(current_user_id and record["user_id"] == current_user_id),
    }


def request_share_context():
    share_kind = request.values.get("share_context_kind", "").strip().lower()
    share_token = request.values.get("share_context_token", "").strip()
    if share_kind in {"file", "folder", "event"} and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", share_token):
        return share_context_from_token(share_kind, share_token)
    return None


def accessible_event(event_id, require_owner=False, share_context=None, include_deleted=False):
    event = event_record(event_id, include_deleted=include_deleted)
    if not event:
        return None
    if session.get("user_id") and event["user_id"] == session["user_id"]:
        return {**event, "can_edit": True, "access_via": "owner"}
    if require_owner:
        return None
    if share_context and share_context["kind"] == "event" and share_context["owner_id"] == event["user_id"]:
        if event["id"] == share_context["item_id"]:
            return {**event, "can_edit": False, "access_via": "event_link"}
    return None


def accessible_folder(folder_id, require_owner=False, share_context=None, include_deleted=False):
    folder = folder_record(folder_id, include_deleted=include_deleted)
    if not folder:
        return None
    if session.get("user_id") and folder["user_id"] == session["user_id"]:
        return {**folder, "can_edit": True, "access_via": "owner"}
    if require_owner:
        return None
    if share_context and share_context["kind"] == "folder" and share_context["owner_id"] == folder["user_id"]:
        if folder["id"] == share_context["item_id"] or folder_is_within(folder["id"], share_context["item_id"]):
            return {**folder, "can_edit": False, "access_via": "folder_link"}
    if share_context and share_context["kind"] == "event" and share_context["owner_id"] == folder["user_id"]:
        if folder.get("event_id") == share_context["item_id"]:
            return {**folder, "can_edit": False, "access_via": "event_link"}
    return None


def accessible_file(file_id, require_owner=False, share_context=None):
    record = file_record(file_id)
    if not record:
        return None
    if session.get("user_id") and record["user_id"] == session["user_id"]:
        return {**record, "can_edit": True, "access_via": "owner"}
    if require_owner:
        return None
    if share_context and share_context["owner_id"] == record["user_id"]:
        if share_context["kind"] == "file" and share_context["item_id"] == record["id"]:
            return {**record, "can_edit": False, "access_via": "file_link"}
        if share_context["kind"] == "folder" and record["folder_id"] and folder_is_within(record["folder_id"], share_context["item_id"]):
            return {**record, "can_edit": False, "access_via": "folder_link"}
        if share_context["kind"] == "event" and record.get("event_id") == share_context["item_id"]:
            return {**record, "can_edit": False, "access_via": "event_link"}
    return None


def redirect_to_workspace(default=None):
    """Return to the current dashboard workspace when it is supplied safely."""
    target = request.form.get("return_to") or request.args.get("return_to") or request.referrer
    if target:
        parsed = urlparse(target)
        allowed_paths = {url_for("dashboard")}
        share_context = request_share_context()
        if share_context and share_context["kind"] == "folder":
            allowed_paths.add(url_for("public_folder", share_token=share_context["token"]))
        if share_context and share_context["kind"] == "event":
            allowed_paths.add(url_for("public_event", share_token=share_context["token"]))
        if (not parsed.netloc or parsed.netloc == request.host) and parsed.path in allowed_paths:
            return redirect(target)
    return redirect(default or url_for("dashboard"))


def workspace_return_url(default=None):
    """Return a safe dashboard URL for links and form return targets."""
    target = request.args.get("return_to") or request.referrer
    if target:
        parsed = urlparse(target)
        allowed_paths = {url_for("dashboard")}
        share_context = request_share_context()
        if share_context and share_context["kind"] == "folder":
            allowed_paths.add(url_for("public_folder", share_token=share_context["token"]))
        if share_context and share_context["kind"] == "event":
            allowed_paths.add(url_for("public_event", share_token=share_context["token"]))
        if (not parsed.netloc or parsed.netloc == request.host) and parsed.path in allowed_paths:
            return target
    return default or url_for("dashboard")


def folder_descendants(folder_id, owner_id=None, include_deleted=False):
    """Return descendant IDs using server-side ownership-scoped traversal."""
    owner_id = session["user_id"] if owner_id is None else owner_id
    descendants = []
    pending = [folder_id]
    while pending:
        current = pending.pop()
        cursor = get_db().cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id FROM folders WHERE user_id = %s AND parent_id = %s AND is_deleted = %s",
                (owner_id, current, include_deleted),
            )
            children = [row["id"] for row in cursor.fetchall()]
        finally:
            cursor.close()
        descendants.extend(children)
        pending.extend(children)
    return descendants


def folder_sizes(cursor, folder_ids, include_deleted=False, owner_id=None):
    """Return recursive file-size totals for the supplied folder IDs."""
    if not folder_ids:
        return {}
    owner_id = session["user_id"] if owner_id is None else owner_id
    placeholders = ",".join(["%s"] * len(folder_ids))
    cursor.execute(
        f"""
        WITH RECURSIVE folder_tree (root_id, folder_id) AS (
            SELECT id, id
            FROM folders
            WHERE user_id = %s AND is_deleted = %s AND id IN ({placeholders})
            UNION ALL
            SELECT folder_tree.root_id, child.id
            FROM folder_tree
            JOIN folders AS child ON child.parent_id = folder_tree.folder_id
            WHERE child.user_id = %s AND child.is_deleted = %s
        )
        SELECT folder_tree.root_id, COALESCE(SUM(files.file_size), 0) AS total_size
        FROM folder_tree
        LEFT JOIN files ON files.folder_id = folder_tree.folder_id
            AND files.user_id = %s AND files.is_deleted = %s
        GROUP BY folder_tree.root_id
        """,
        (owner_id, include_deleted, *folder_ids, owner_id, include_deleted, owner_id, include_deleted),
    )
    return {row["root_id"]: row["total_size"] or 0 for row in cursor.fetchall()}


def event_sizes(cursor, event_ids, include_deleted=False, owner_id=None):
    """Return actual file-size totals for Events, including every nested folder."""
    if not event_ids:
        return {}
    placeholders = ",".join(["%s"] * len(event_ids))
    owner_condition = " AND user_id = %s" if owner_id is not None else ""
    values = (include_deleted, *event_ids, owner_id) if owner_id is not None else (include_deleted, *event_ids)
    cursor.execute(
        "SELECT event_id, COALESCE(SUM(file_size), 0) AS total_size "
        f"FROM files WHERE is_deleted = %s AND event_id IN ({placeholders}){owner_condition} "
        "GROUP BY event_id",
        values,
    )
    return {row["event_id"]: row["total_size"] or 0 for row in cursor.fetchall()}


def folder_paths(folders):
    """Build display paths for a user's folder tree without cross-user lookups."""
    folders_by_id = {folder["id"]: folder for folder in folders}
    paths = {}

    def build_path(folder_id, seen=None):
        if folder_id in paths:
            return paths[folder_id]
        seen = set() if seen is None else seen
        folder = folders_by_id.get(folder_id)
        if not folder or folder_id in seen:
            return "Library"
        parent_id = folder.get("parent_id")
        parent_path = build_path(parent_id, seen | {folder_id}) if parent_id else "Library"
        paths[folder_id] = f"{parent_path} / {folder['name']}"
        return paths[folder_id]

    for folder_id in folders_by_id:
        build_path(folder_id)
    return paths


def file_location(record):
    """Return a safe display location for preview metadata."""
    if record.get("event_id"):
        event = query_one(
            "SELECT id, name FROM events WHERE id = %s AND user_id = %s AND is_deleted = FALSE",
            (record["event_id"], record["user_id"]),
        )
        root = f"Events / {event['name']}" if event else "Events"
    else:
        root = "Library"
    folder_id = record.get("folder_id")
    if not folder_id:
        return root
    parts = []
    while folder_id:
        folder = folder_record(folder_id)
        if folder and folder["user_id"] != record["user_id"]:
            break
        if not folder:
            break
        parts.append(folder["name"])
        folder_id = folder["parent_id"]
    return " / ".join([root, *reversed(parts)])


def normalized_calendar_month(year=None, month=None):
    today = date.today()
    try:
        year = int(year) if year is not None else today.year
    except (TypeError, ValueError):
        year = today.year
    try:
        month = int(month) if month is not None else today.month
    except (TypeError, ValueError):
        month = today.month
    if year < 1 or year > 9999:
        year = today.year
    if month < 1 or month > 12:
        month = today.month
    return year, month


def shift_calendar_month(year, month, delta):
    total_months = (year * 12) + (month - 1) + delta
    new_year = total_months // 12
    new_month = (total_months % 12) + 1
    if new_year < 1:
        new_year = 1
    return new_year, new_month


def sunday_first_month_weeks(year, month):
    """Return calendar weeks with Sunday as index 0 and no timezone-sensitive parsing."""
    return calendar_module.Calendar(firstweekday=calendar_module.SUNDAY).monthdayscalendar(year, month)


def build_events_calendar_context(year=None, month=None, url_builder=None):
    year, month = normalized_calendar_month(year, month)
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, event_date, event_type FROM events "
            "WHERE user_id = %s AND is_deleted = FALSE AND event_date IS NOT NULL "
            "AND YEAR(event_date) = %s AND MONTH(event_date) = %s ORDER BY event_date, name",
            (session["user_id"], year, month),
        )
        events = cursor.fetchall()
    except MySQLError:
        app.logger.exception("Events calendar database error")
        flash("Could not load the Events calendar. Please try again.", "error")
        events = []
    finally:
        cursor.close()
    events_by_day = {}
    for event in events:
        events_by_day.setdefault(event["event_date"].day, []).append(event)
    previous_year, previous_month = shift_calendar_month(year, month, -1)
    next_year, next_month = shift_calendar_month(year, month, 1)
    weeks = sunday_first_month_weeks(year, month)
    day_urls = {}
    if url_builder:
        for week in weeks:
            for day in week:
                if day:
                    day_urls[day] = url_builder(event_date=date(year, month, day).isoformat(), calendar=None)
    return {
        "month_name": calendar_module.month_name[month],
        "year": year,
        "month": month,
        "weeks": weeks,
        "events_by_day": events_by_day,
        "calendar_previous_url": url_builder(calendar="open", calendar_year=previous_year, calendar_month=previous_month) if url_builder else None,
        "calendar_next_url": url_builder(calendar="open", calendar_year=next_year, calendar_month=next_month) if url_builder else None,
        "calendar_day_urls": day_urls,
    }


def preview_kind(record):
    classification = classify_file_type(record)
    mime_type = classification["mime_type"]
    extension = classification["extension"]
    if classification["key"] in {"image", "pdf", "video", "audio", "powerpoint", "spreadsheet"}:
        return classification["key"]
    if mime_type.startswith("text/") or extension in {".txt", ".md", ".log"}:
        return "text"
    return "unavailable"


def record_path(record):
    stored_name = record["stored_filename"]
    if stored_name != Path(stored_name).name:
        abort(404)
    return user_directory(record["user_id"]) / stored_name


class PresentationPreviewError(RuntimeError):
    pass


def detect_libreoffice_binary():
    configured = os.getenv("LIBREOFFICE_BINARY", "").strip().strip('"')
    if configured:
        resolved = shutil.which(configured)
        if resolved:
            return str(Path(resolved).resolve())
        if os.name == "nt" and Path(configured).is_file():
            return str(Path(configured).resolve())
        raise PresentationPreviewError(
            f"LIBREOFFICE_BINARY is set to '{configured}', but that executable could not be found or run."
        )

    for command in ("libreoffice", "soffice"):
        resolved = shutil.which(command)
        if resolved:
            return str(Path(resolved).resolve())

    if os.name == "nt":
        windows_binary = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")
        if windows_binary.is_file():
            return str(windows_binary.resolve())

    raise PresentationPreviewError(
        "LibreOffice was not found. Set LIBREOFFICE_BINARY or install 'libreoffice'/'soffice' on PATH."
    )


_LIBREOFFICE_BINARY_PATH = None


def libreoffice_binary():
    global _LIBREOFFICE_BINARY_PATH
    if _LIBREOFFICE_BINARY_PATH:
        return _LIBREOFFICE_BINARY_PATH
    try:
        _LIBREOFFICE_BINARY_PATH = detect_libreoffice_binary()
    except PresentationPreviewError as error:
        app.logger.error("LibreOffice detection failed: %s", error)
        raise
    app.logger.info("LibreOffice detected at startup: %s", _LIBREOFFICE_BINARY_PATH)
    return _LIBREOFFICE_BINARY_PATH


def log_libreoffice_path_debug():
    app.logger.info(
        "LibreOffice PATH lookup: libreoffice=%r, soffice=%r",
        shutil.which("libreoffice"),
        shutil.which("soffice"),
    )


log_libreoffice_path_debug()
try:
    libreoffice_binary()
except PresentationPreviewError:
    # Presentation requests will return a clear 503 while the rest of the
    # file service remains available.
    pass


def presentation_fallback_files(record):
    """Return an optional Microsoft PowerPoint-exported PDF or PNG slide set."""
    owner_directory = PRESENTATION_PRE_RENDERED_FOLDER / str(int(record["user_id"]))
    slide_directory = owner_directory / str(int(record["id"]))
    if slide_directory.is_dir():
        step_pattern = re.compile(r"^slide-(\d+)-step-(\d+)\.png$", re.IGNORECASE)
        step_groups = {}
        for path in slide_directory.iterdir():
            match = step_pattern.match(path.name) if path.is_file() else None
            if match:
                step_groups.setdefault(int(match.group(1)), {})[int(match.group(2))] = path
        if step_groups:
            ordered_groups = []
            for slide_number in range(1, max(step_groups) + 1):
                numbered_steps = step_groups.get(slide_number, {})
                if 0 not in numbered_steps:
                    app.logger.error(
                        "Ignoring PowerPoint animation frames for file_id=%s: slide %d has no step 0",
                        record["id"],
                        slide_number,
                    )
                    ordered_groups = []
                    break
                ordered_steps = [numbered_steps[index] for index in range(max(numbered_steps) + 1) if index in numbered_steps]
                if len(ordered_steps) != max(numbered_steps) + 1:
                    app.logger.error(
                        "Ignoring PowerPoint animation frames for file_id=%s: slide %d step numbers are not contiguous",
                        record["id"],
                        slide_number,
                    )
                    ordered_groups = []
                    break
                ordered_groups.append(ordered_steps)
            if ordered_groups and len(ordered_groups) == max(step_groups):
                return {
                    "kind": "png-steps",
                    "files": [path for group in ordered_groups for path in group],
                    "step_groups": ordered_groups,
                }
    pdf_candidates = [owner_directory / f"{int(record['id'])}.pdf", slide_directory / "slides.pdf"]
    for candidate in pdf_candidates:
        if candidate.is_file():
            return {"kind": "pdf", "files": [candidate]}
    if slide_directory.is_dir():
        slide_pattern = re.compile(r"^slide-(\d+)\.png$", re.IGNORECASE)
        numbered_slides = []
        for path in slide_directory.iterdir():
            match = slide_pattern.match(path.name) if path.is_file() else None
            if match:
                numbered_slides.append((int(match.group(1)), path))
        numbered_slides.sort(key=lambda item: item[0])
        slides = [path for _number, path in numbered_slides]
        if slides:
            return {"kind": "png", "files": slides}
    return None


def presentation_fallback_signature(record):
    fallback = presentation_fallback_files(record)
    if not fallback:
        return "none"
    parts = [fallback["kind"]]
    for path in fallback["files"]:
        stat = path.stat()
        parts.append(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}")
    return "|".join(parts)


def pptx_font_names(path):
    """Read explicit and theme Latin/EA/complex-script fonts from an OOXML deck."""
    import xml.etree.ElementTree as element_tree

    fonts = set()
    embedded_font_count = 0
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.startswith("ppt/") and name.endswith(".xml")]
            embedded_font_count = sum(1 for name in archive.namelist() if name.startswith("ppt/fonts/") and not name.endswith("/"))
            for name in names:
                try:
                    root = element_tree.fromstring(archive.read(name))
                except (KeyError, element_tree.ParseError):
                    continue
                is_theme = name.startswith("ppt/theme/")
                for element in root.iter():
                    local_name = element.tag.rsplit("}", 1)[-1]
                    typeface = element.attrib.get("typeface", "").strip()
                    if not typeface or typeface.startswith("+"):
                        continue
                    if is_theme and local_name not in {"latin", "ea", "cs"}:
                        continue
                    fonts.add(typeface)
    except (OSError, zipfile.BadZipFile) as error:
        app.logger.warning("Could not inspect presentation fonts in %s: %s", path.name, error)
    return sorted(fonts, key=str.casefold), embedded_font_count


def pptx_animation_sequences(path):
    """Inspect OOXML timing metadata without attempting to render its effects."""
    import xml.etree.ElementTree as element_tree

    sequences = {}
    slide_pattern = re.compile(r"^ppt/slides/slide(\d+)\.xml$")
    try:
        with zipfile.ZipFile(path) as archive:
            slide_parts = []
            for name in archive.namelist():
                match = slide_pattern.match(name)
                if match:
                    slide_parts.append((int(match.group(1)), name))
            for slide_number, name in sorted(slide_parts):
                try:
                    root = element_tree.fromstring(archive.read(name))
                except (KeyError, element_tree.ParseError):
                    continue
                shape_names = {}
                for element in root.iter():
                    if element.tag.rsplit("}", 1)[-1] == "cNvPr" and element.attrib.get("id"):
                        shape_names[element.attrib["id"]] = element.attrib.get("name") or f"Shape {element.attrib['id']}"
                main_sequences = [
                    element for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "cTn" and element.attrib.get("nodeType") == "mainSeq"
                ]
                steps = []
                for main_sequence in main_sequences:
                    parent_map = {child: parent for parent in main_sequence.iter() for child in list(parent)}
                    triggered_nodes = []
                    for candidate in main_sequence.iter():
                        if candidate is main_sequence or candidate.tag.rsplit("}", 1)[-1] != "cTn":
                            continue
                        has_click_trigger = any(
                            condition.tag.rsplit("}", 1)[-1] == "cond"
                            and condition.attrib.get("evt") in {"onNext", "onClick"}
                            for child in list(candidate)
                            if child.tag.rsplit("}", 1)[-1] == "stCondLst"
                            for condition in child.iter()
                        )
                        if has_click_trigger:
                            triggered_nodes.append(candidate)
                    triggered_set = set(triggered_nodes)
                    click_groups = []
                    for candidate in triggered_nodes:
                        ancestor = parent_map.get(candidate)
                        while ancestor is not None and ancestor is not main_sequence and ancestor not in triggered_set:
                            ancestor = parent_map.get(ancestor)
                        if ancestor not in triggered_set:
                            click_groups.append(candidate)
                    if not click_groups:
                        click_groups = [
                            element for element in main_sequence.iter()
                            if element.tag.rsplit("}", 1)[-1] == "cTn"
                            and element.attrib.get("nodeType") == "clickEffect"
                        ]
                    for click_group in click_groups:
                        targets = []
                        effects = []
                        for element in click_group.iter():
                            local_name = element.tag.rsplit("}", 1)[-1]
                            if local_name == "spTgt" and element.attrib.get("spid"):
                                shape_id = element.attrib["spid"]
                                target = {"shape_id": shape_id, "name": shape_names.get(shape_id, f"Shape {shape_id}")}
                                if target not in targets:
                                    targets.append(target)
                            elif local_name == "animEffect":
                                effect = element.attrib.get("filter") or element.attrib.get("transition") or "effect"
                                if effect not in effects:
                                    effects.append(effect)
                            elif local_name == "animMotion" and "motion" not in effects:
                                effects.append("motion")
                            elif local_name == "set" and "appear/state" not in effects:
                                effects.append("appear/state")
                            elif local_name == "anim" and "property animation" not in effects:
                                effects.append("property animation")
                        steps.append({"targets": targets, "effects": effects})
                if not steps:
                    click_effects = [
                        element for element in root.iter()
                        if element.tag.rsplit("}", 1)[-1] == "cTn" and element.attrib.get("nodeType") == "clickEffect"
                    ]
                    steps = [{"targets": [], "effects": []} for _element in click_effects]
                if steps:
                    sequences[slide_number] = {"click_steps": len(steps), "steps": steps}
    except (OSError, zipfile.BadZipFile) as error:
        app.logger.warning("Could not inspect presentation animation timing in %s: %s", path.name, error)
    return sequences


def convert_legacy_presentation_for_font_inspection(source, work_directory, profile_directory):
    inspection_directory = work_directory / "font-inspection"
    inspection_directory.mkdir()
    result = subprocess.run(
        [
            libreoffice_binary(),
            "--headless",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            f"-env:UserInstallation={profile_directory.resolve().as_uri()}",
            "--convert-to",
            "pptx:Impress MS PowerPoint 2007 XML",
            "--outdir",
            str(inspection_directory),
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    converted = list(inspection_directory.glob("*.pptx"))
    if result.returncode != 0 or not converted:
        details = (result.stderr or result.stdout or "no diagnostic output").strip()
        app.logger.warning("Could not create a PPTX copy for legacy PPT font inspection: %s", details)
        return None
    return converted[0]


def log_presentation_font_report(source, work_directory, profile_directory):
    inspection_source = source
    if source.suffix.lower() in {".ppt", ".pps"}:
        try:
            inspection_source = convert_legacy_presentation_for_font_inspection(source, work_directory, profile_directory)
        except (OSError, subprocess.TimeoutExpired) as error:
            app.logger.warning("Legacy PPT font inspection failed: %s", error)
            inspection_source = None
    if not inspection_source or inspection_source.suffix.lower() not in {".pptx", ".ppsx"}:
        app.logger.warning("Font inspection is unavailable for presentation format %s", source.suffix.lower())
        return {}

    animation_sequences = pptx_animation_sequences(inspection_source)
    if animation_sequences:
        app.logger.info("PowerPoint on-click animation sequences detected: source=%s slides=%s", source.name, animation_sequences)

    fonts, embedded_font_count = pptx_font_names(inspection_source)
    app.logger.info(
        "Presentation font inspection: source=%s fonts=%s embedded_font_files=%d",
        source.name,
        fonts or "none declared",
        embedded_font_count,
    )
    font_match_binary = shutil.which("fc-match")
    if not font_match_binary:
        app.logger.warning("Font substitution diagnostics unavailable because fc-match is not on PATH")
        return animation_sequences
    for requested_font in fonts:
        try:
            match = subprocess.run(
                [font_match_binary, "-f", "%{family}|%{file}\n", requested_font],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            app.logger.warning("Font lookup failed for %r: %s", requested_font, error)
            continue
        matched_line = next((line.strip() for line in match.stdout.splitlines() if line.strip()), "")
        matched_family, _, matched_file = matched_line.partition("|")
        requested_key = requested_font.casefold()
        matched_families = {family.strip().casefold() for family in matched_family.split(",")}
        if requested_key not in matched_families:
            app.logger.warning(
                "Presentation font fallback: requested=%r matched=%r file=%r",
                requested_font,
                matched_family or "unknown",
                matched_file or "unknown",
            )
        else:
            app.logger.info("Presentation font available: requested=%r file=%r", requested_font, matched_file)
    return animation_sequences


_FONTCONFIG_SIGNATURE = None


def fontconfig_signature():
    """Fingerprint runtime fonts so a font-layer change invalidates cached slides."""
    global _FONTCONFIG_SIGNATURE
    if _FONTCONFIG_SIGNATURE:
        return _FONTCONFIG_SIGNATURE
    font_list_binary = shutil.which("fc-list")
    if not font_list_binary:
        _FONTCONFIG_SIGNATURE = "fontconfig-unavailable"
        return _FONTCONFIG_SIGNATURE
    try:
        result = subprocess.run(
            [font_list_binary, "-f", "%{file}|%{family}|%{style}\n"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        catalog = "\n".join(sorted(line.strip() for line in result.stdout.splitlines() if line.strip()))
        _FONTCONFIG_SIGNATURE = hashlib.sha256(catalog.encode("utf-8")).hexdigest()[:16] if catalog else "empty"
    except (OSError, subprocess.TimeoutExpired) as error:
        app.logger.warning("Could not fingerprint the runtime font catalog: %s", error)
        _FONTCONFIG_SIGNATURE = "fontconfig-error"
    app.logger.info("Presentation font catalog signature: %s", _FONTCONFIG_SIGNATURE)
    return _FONTCONFIG_SIGNATURE


def presentation_preview_cache(record):
    source = record_path(record)
    if not source.is_file():
        raise PresentationPreviewError("The original presentation is no longer available.")
    stat = source.stat()
    fingerprint = hashlib.sha256(
        (
            f"{PRESENTATION_PREVIEW_RENDERER_VERSION}:{record['stored_filename']}:{stat.st_size}:"
            f"{stat.st_mtime_ns}:{PRESENTATION_PREVIEW_DPI}:{fontconfig_signature()}:"
            f"{presentation_fallback_signature(record)}"
        ).encode("utf-8")
    ).hexdigest()[:20]
    return PRESENTATION_PREVIEW_FOLDER / str(record["user_id"]) / f"{record['id']}-{fingerprint}"


def png_pixel_dimensions(path):
    with path.open("rb") as image:
        header = image.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise PresentationPreviewError(f"Pre-rendered slide {path.name} is not a valid PNG image.")
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def rasterize_presentation_pdf(pdf_path, cache_directory, pymupdf, renderer):
    document = pymupdf.open(pdf_path)
    try:
        if document.page_count < 1:
            raise PresentationPreviewError("The presentation contains no renderable slides.")
        slide_names = []
        page_manifest = []
        for index, page in enumerate(document):
            # PyMuPDF rasterizes the complete PDF page in one operation. No
            # slide element is reconstructed, repositioned, or independently scaled.
            pixmap = page.get_pixmap(dpi=PRESENTATION_PREVIEW_DPI, alpha=False, annots=True)
            slide_name = f"slide-{index + 1}.png"
            temporary_slide = cache_directory / f".{slide_name}.tmp"
            pixmap.save(str(temporary_slide), output="png")
            temporary_slide.replace(cache_directory / slide_name)
            slide_names.append(slide_name)
            page_manifest.append({
                "file": slide_name,
                "width": pixmap.width,
                "height": pixmap.height,
                "page_width_points": round(float(page.rect.width), 6),
                "page_height_points": round(float(page.rect.height), 6),
            })
    finally:
        document.close()
    return {
        "slide_count": len(slide_names),
        "width": page_manifest[0]["width"],
        "height": page_manifest[0]["height"],
        "slides": slide_names,
        "steps": [[slide_name] for slide_name in slide_names],
        "pages": page_manifest,
        "dpi": PRESENTATION_PREVIEW_DPI,
        "renderer": renderer,
        "animation_mode": "static-final-frame",
    }


def copy_prerendered_png_slides(slides, cache_directory):
    slide_names = []
    page_manifest = []
    for index, source_slide in enumerate(slides):
        width, height = png_pixel_dimensions(source_slide)
        slide_name = f"slide-{index + 1}.png"
        temporary_slide = cache_directory / f".{slide_name}.tmp"
        shutil.copyfile(source_slide, temporary_slide)
        temporary_slide.replace(cache_directory / slide_name)
        slide_names.append(slide_name)
        page_manifest.append({"file": slide_name, "width": width, "height": height})
    return {
        "slide_count": len(slide_names),
        "width": page_manifest[0]["width"],
        "height": page_manifest[0]["height"],
        "slides": slide_names,
        "steps": [[slide_name] for slide_name in slide_names],
        "pages": page_manifest,
        "dpi": None,
        "renderer": "microsoft-powerpoint-png-export",
        "animation_mode": "static-final-frame",
    }


def copy_prerendered_png_steps(step_groups, cache_directory):
    slide_names = []
    cached_step_groups = []
    page_manifest = []
    for slide_index, source_steps in enumerate(step_groups, start=1):
        cached_steps = []
        expected_dimensions = None
        for step_index, source_step in enumerate(source_steps):
            dimensions = png_pixel_dimensions(source_step)
            if expected_dimensions is None:
                expected_dimensions = dimensions
            elif dimensions != expected_dimensions:
                raise PresentationPreviewError(
                    f"Pre-rendered animation frames for slide {slide_index} do not have matching dimensions."
                )
            step_name = f"slide-{slide_index}-step-{step_index}.png"
            temporary_step = cache_directory / f".{step_name}.tmp"
            shutil.copyfile(source_step, temporary_step)
            temporary_step.replace(cache_directory / step_name)
            cached_steps.append(step_name)
        slide_names.append(cached_steps[0])
        cached_step_groups.append(cached_steps)
        page_manifest.append({"file": cached_steps[0], "width": expected_dimensions[0], "height": expected_dimensions[1]})
    return {
        "slide_count": len(slide_names),
        "width": page_manifest[0]["width"],
        "height": page_manifest[0]["height"],
        "slides": slide_names,
        "steps": cached_step_groups,
        "pages": page_manifest,
        "dpi": None,
        "renderer": "microsoft-powerpoint-animation-frames",
        "animation_mode": "pre-rendered-click-steps",
    }


def render_presentation_preview(record):
    """Render via LibreOffice/PDF so the browser only scales finished slide pixels."""
    cache_directory = presentation_preview_cache(record)
    manifest_path = cache_directory / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            cached_frames = [
                name for group in manifest.get("steps", []) for name in group
            ] or manifest.get("slides", [])
            if manifest.get("slide_count") and cached_frames and all((cache_directory / name).is_file() for name in cached_frames):
                return cache_directory, manifest
        except (OSError, ValueError, TypeError):
            pass

    source = record_path(record)
    cache_directory.mkdir(parents=True, exist_ok=True)
    try:
        import pymupdf
    except ImportError as error:
        raise PresentationPreviewError("The PDF image renderer is not installed.") from error

    try:
        with tempfile.TemporaryDirectory(prefix="jfcm-presentation-") as temporary:
            work_directory = Path(temporary)
            profile_directory = work_directory / "libreoffice-profile"
            output_directory = work_directory / "converted"
            output_directory.mkdir()
            fallback = presentation_fallback_files(record)
            if fallback:
                app.logger.info(
                    "Using Microsoft PowerPoint pre-rendered %s fallback for presentation file_id=%s",
                    fallback["kind"].upper(),
                    record["id"],
                )
                if fallback["kind"] == "pdf":
                    manifest = rasterize_presentation_pdf(
                        fallback["files"][0], cache_directory, pymupdf, "microsoft-powerpoint-pdf-export"
                    )
                elif fallback["kind"] == "png-steps":
                    manifest = copy_prerendered_png_steps(fallback["step_groups"], cache_directory)
                else:
                    manifest = copy_prerendered_png_slides(fallback["files"], cache_directory)
                if source.suffix.lower() in {".pptx", ".ppsx"}:
                    animation_sequences = pptx_animation_sequences(source)
                    manifest["animation_sequences"] = animation_sequences
                    if fallback["kind"] == "png-steps":
                        for slide_number, sequence in animation_sequences.items():
                            actual_frames = len(manifest["steps"][slide_number - 1]) if slide_number <= len(manifest["steps"]) else 0
                            expected_frames = sequence["click_steps"] + 1
                            if actual_frames != expected_frames:
                                app.logger.warning(
                                    "PowerPoint animation frame count differs from detected timing: file_id=%s slide=%d "
                                    "expected_frames=%d actual_frames=%d",
                                    record["id"],
                                    slide_number,
                                    expected_frames,
                                    actual_frames,
                                )
            else:
                animation_sequences = log_presentation_font_report(source, work_directory, profile_directory)
                result = subprocess.run(
                    [
                        libreoffice_binary(),
                        "--headless",
                        "--nologo",
                        "--nodefault",
                        "--nofirststartwizard",
                        f"-env:UserInstallation={profile_directory.resolve().as_uri()}",
                        "--convert-to",
                        "pdf:impress_pdf_Export",
                        "--outdir",
                        str(output_directory),
                        str(source),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                conversion_output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
                if conversion_output:
                    app.logger.info("LibreOffice presentation conversion output: %s", conversion_output)
                pdf_files = list(output_directory.glob("*.pdf"))
                if result.returncode != 0 or not pdf_files:
                    details = conversion_output or "LibreOffice did not create a PDF."
                    app.logger.error("Presentation conversion failed: %s", details)
                    raise PresentationPreviewError(
                        "The presentation could not be converted for preview. "
                        "A Microsoft PowerPoint-exported PDF or PNG fallback can be configured."
                    )
                manifest = rasterize_presentation_pdf(pdf_files[0], cache_directory, pymupdf, "libreoffice-pdf")
                manifest["animation_sequences"] = animation_sequences
                if animation_sequences:
                    app.logger.warning(
                        "LibreOffice PDF export flattened %d slide(s) containing on-click animation sequences for file_id=%s. "
                        "Use slide-N-step-M.png PowerPoint exports to preserve click states.",
                        len(animation_sequences),
                        record["id"],
                    )
    except subprocess.TimeoutExpired as error:
        raise PresentationPreviewError("The presentation preview took too long to render.") from error
    except OSError as error:
        app.logger.exception("Presentation preview renderer error")
        raise PresentationPreviewError("The presentation preview renderer could not be started.") from error

    temporary_manifest = cache_directory / ".manifest.json.tmp"
    temporary_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    temporary_manifest.replace(manifest_path)
    return cache_directory, manifest


def presentation_share_params(share_context):
    if not share_context:
        return {}
    return {
        "share_context_kind": share_context["kind"],
        "share_context_token": share_context["token"],
    }


FILE_TYPE_DEFINITIONS = (
    {
        "key": "image",
        "label": "Image",
        "icon": "Image.png",
        "mime_prefixes": ("image/",),
        "extensions": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tif", ".tiff"},
    },
    {
        "key": "pdf",
        "label": "PDF",
        "icon": "PDF.png",
        "mime_types": {"application/pdf"},
        "extensions": {".pdf"},
    },
    {
        "key": "document",
        "label": "Document",
        "icon": "Word.png",
        "mime_types": {
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.oasis.opendocument.text",
            "application/rtf",
            "text/rtf",
            "application/x-rtf",
            "text/plain",
            "text/markdown",
        },
        "extensions": {".doc", ".docx", ".odt", ".rtf", ".txt", ".md"},
    },
    {
        "key": "spreadsheet",
        "label": "Spreadsheet",
        "icon": "Spreadsheet.png",
        "mime_types": {
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.oasis.opendocument.spreadsheet",
            "text/csv",
            "text/tab-separated-values",
        },
        "extensions": {".xls", ".xlsx", ".ods", ".csv", ".tsv"},
    },
    {
        "key": "powerpoint",
        "label": "PowerPoint",
        "icon": "PPT.png",
        "mime_types": {
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
            "application/vnd.oasis.opendocument.presentation",
        },
        "extensions": {".ppt", ".pptx", ".pps", ".ppsx", ".odp"},
    },
    {
        "key": "video",
        "label": "Video",
        "icon": "Video.png",
        "mime_prefixes": ("video/",),
        "extensions": {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"},
    },
    {
        "key": "audio",
        "label": "Audio",
        "icon": "Audio.png",
        "mime_prefixes": ("audio/",),
        "extensions": {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"},
    },
    {
        "key": "zip",
        "label": "ZIP",
        "icon": "Zip.png",
        "mime_types": {
            "application/zip",
            "application/x-zip",
            "application/x-zip-compressed",
            "application/x-rar-compressed",
            "application/x-7z-compressed",
            "application/x-tar",
            "application/gzip",
            "application/x-gzip",
        },
        "extensions": {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz"},
    },
)

EVENT_TYPE_OPTIONS = (
    ("event", "Event", "Event.png"),
    ("heart", "Heart", "Heart.png"),
    ("birthday", "Birthday", "Birthday.png"),
    ("graduation", "Graduation", "Graduation.png"),
    ("celebration", "Celebration", "Celebration.png"),
    ("fellowship", "Fellowship", "Fellowship.png"),
    ("water", "Water", "Water.png"),
    ("supper", "Supper", "Supper.png"),
    ("camp", "Camp", "Camp.png"),
    ("conference", "Conference", "Conference.png"),
)
EVENT_TYPE_FILE_MAP = {key: filename for key, _label, filename in EVENT_TYPE_OPTIONS}


def classify_file_type(file_or_mime, filename=None):
    if isinstance(file_or_mime, dict):
        mime_type = (file_or_mime.get("mime_type") or "").lower().strip()
        filename = file_or_mime.get("original_filename") or file_or_mime.get("name") or filename or ""
    else:
        mime_type = (file_or_mime or "").lower().strip()
        filename = filename or ""
    extension = Path(filename).suffix.lower()

    for definition in FILE_TYPE_DEFINITIONS:
        mime_types = definition.get("mime_types", set())
        mime_prefixes = definition.get("mime_prefixes", tuple())
        extensions = definition.get("extensions", set())
        if mime_type in mime_types or any(mime_type.startswith(prefix) for prefix in mime_prefixes) or extension in extensions:
            return {
                "key": definition["key"],
                "label": definition["label"],
                "icon": definition["icon"],
                "mime_type": mime_type,
                "extension": extension,
            }

    return {
        "key": "other",
        "label": "Other",
        "icon": "File.png",
        "mime_type": mime_type,
        "extension": extension,
    }


def clean_file_type(file_or_mime, filename=None):
    return classify_file_type(file_or_mime, filename)["label"]


def file_type_key(file_or_mime, filename=None):
    return classify_file_type(file_or_mime, filename)["key"]


def file_type_icon(file_or_mime, filename=None):
    return classify_file_type(file_or_mime, filename)["icon"]


def event_icon_file(event_type):
    return EVENT_TYPE_FILE_MAP.get((event_type or "").strip().lower(), EVENT_TYPE_FILE_MAP["event"])


def event_type_label(event_type):
    labels = {
        "event": "Event",
        "heart": "Anniversary",
        "balloon": "Birthday",
        "birthday": "Birthday",
        "graduation": "Graduation",
        "celebration": "Celebration",
        "fellowship": "Fellowship",
        "water": "Water Baptism",
        "supper": "Lord's Supper",
        "camp": "Camp",
        "conference": "Conference",
    }
    return labels.get((event_type or "").strip().lower(), "Event")


def move_destination_options(owner_id):
    """Return an ordered, flattened destination tree for the Move modal."""
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, parent_id, event_id FROM folders "
            "WHERE user_id = %s AND is_deleted = FALSE ORDER BY name",
            (owner_id,),
        )
        folders = cursor.fetchall()
        cursor.execute(
            "SELECT id, name, event_type FROM events "
            "WHERE user_id = %s AND is_deleted = FALSE ORDER BY event_date, name",
            (owner_id,),
        )
        events = cursor.fetchall()
    finally:
        cursor.close()

    children = {}
    for folder in folders:
        children.setdefault((folder.get("event_id"), folder.get("parent_id")), []).append(folder)

    destinations = [{
        "value": "library",
        "kind": "library",
        "name": "JFCM Library",
        "depth": 0,
        "folder_id": None,
        "event_id": None,
        "ancestor_ids": "",
        "icon_filename": "Folder.png",
    }]

    def append_folders(event_id, parent_id, depth, ancestors):
        for folder in children.get((event_id, parent_id), []):
            destinations.append({
                "value": f"folder:{folder['id']}",
                "kind": "folder",
                "name": folder["name"],
                "depth": depth,
                "folder_id": folder["id"],
                "event_id": folder.get("event_id"),
                "ancestor_ids": ",".join(str(folder_id) for folder_id in ancestors),
                "icon_filename": "Folder.png",
            })
            append_folders(event_id, folder["id"], depth + 1, [*ancestors, folder["id"]])

    append_folders(None, None, 1, [])
    destinations.append({"value": "", "kind": "events", "name": "Events", "depth": 0})
    for event in events:
        destinations.append({
            "value": f"event:{event['id']}",
            "kind": "event",
            "name": event["name"],
            "depth": 1,
            "folder_id": None,
            "event_id": event["id"],
            "ancestor_ids": "",
            "icon_filename": event_icon_file(event.get("event_type")),
        })
        append_folders(event["id"], None, 2, [])
    return destinations


def trash_days_remaining(deleted_at):
    if not deleted_at:
        return ""
    expire_date = deleted_at.date() + timedelta(days=TRASH_RETENTION_DAYS)
    remaining_days = (expire_date - date.today()).days
    if remaining_days <= 0:
        return "Expires today"
    return f"{remaining_days} day{'s' if remaining_days != 1 else ''} left"


def display_name(name):
    """Format stored names for display without changing the stored value."""
    return (name or "").replace("-", " ").replace("_", " ")


def format_datetime(dt):
    """Format datetime to 'Aug 17, 2026 12:21 pm' format."""
    if not dt:
        return ""
    formatted = dt.strftime('%b %d, %Y %I:%M %p')
    formatted = formatted.replace(' 0', ' ', 1)
    return formatted.replace('AM', 'am').replace('PM', 'pm')


@app.context_processor
def utility_processor():
    def readable_size(size):
        size = int(size or 0)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                if unit == "B":
                    return f"{size} B"
                formatted_size = f"{size:.1f}".rstrip("0").rstrip(".")
                return f"{formatted_size} {unit}"
            size /= 1024

    def display_item_size(kind, size):
        normalized_kind = (kind or "").strip().lower()
        normalized_size = int(size or 0)
        if normalized_kind in {"folder", "event"} and normalized_size == 0:
            return "—"
        return readable_size(normalized_size)

    return {
        "readable_size": readable_size,
        "display_item_size": display_item_size,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "clean_file_type": clean_file_type,
        "file_type_key": file_type_key,
        "file_type_icon": file_type_icon,
        "display_name": display_name,
        "format_datetime": format_datetime,
        "event_icon_options": EVENT_TYPE_OPTIONS,
        "event_icon_file": event_icon_file,
        "event_type_label": event_type_label,
        "trash_days_remaining": trash_days_remaining,
        "offline_cache_scope": current_offline_cache_scope(),
    }


@app.route("/")
def index():
    # Keep the landing route session-aware while the dashboard remains the
    # single renderer for authenticated and public workspaces.
    if "user_id" in session:
        if session_is_expired():
            session.clear()
            flash("Your session expired after 7 days of inactivity. Please sign in again.", "error")
        else:
            touch_authenticated_session()
            purge_expired_trash(session["user_id"])
    return redirect(url_for("dashboard"))


@app.get("/privacy")
def privacy_notice():
    return render_template("privacy.html", privacy_contact_email=PRIVACY_CONTACT_EMAIL)


@app.get("/terms")
def terms_of_use():
    return render_template("terms.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect_to_workspace()
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not email or "@" not in email:
            flash("Enter a valid email address.", "error")
        elif not re.fullmatch(r"[a-z0-9_]{3,20}", username):
            flash("Username must be 3-20 characters using letters, numbers, or underscores.", "error")
        elif not password or len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            cursor = None
            try:
                cursor = get_db().cursor()
                cursor.execute(
                    "INSERT INTO users (email, username, password_hash) VALUES (%s, %s, %s)",
                    (email, username, generate_password_hash(password)),
                )
                get_db().commit()
                send_welcome_email(email)
                flash("Account created. Please check your email and sign in.", "success")
                return redirect(url_for("login"))
            except MySQLError as error:
                get_db().rollback()
                if getattr(error, "errno", None) == 1062:
                    flash("That email or username is already in use.", "error")
                else:
                    app.logger.exception("Registration database error")
                    flash("Unable to create the account. Please try again.", "error")
            finally:
                if cursor:
                    cursor.close()
    return render_template("register.html")


@app.get("/login")
def login():
    if "user_id" in session:
        return redirect_to_workspace()
    return render_template("login.html")


@app.post("/login")
def login_post():
    identifier = request.form.get("identifier", "").strip().lower()
    password = request.form.get("password", "")
    if not identifier or not password:
        flash("Enter your email/username and password.", "error")
    else:
        try:
            user = query_one(
                "SELECT id, email, username, password_hash FROM users "
                "WHERE email = %s OR username = %s LIMIT 1",
                (identifier, identifier),
            )
            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email/username or password.", "error")
            else:
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"] or user["email"]
                session[OFFLINE_CACHE_SCOPE_KEY] = secrets.token_urlsafe(24)
                touch_authenticated_session()
                return redirect(url_for("dashboard"))
        except MySQLError:
            app.logger.exception("Login database error")
            flash("Unable to sign in right now. Please try again.", "error")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.get("/storage")
def dashboard():
    if "user_id" not in session:
        return public_dashboard()
    section = request.args.get("section", "files")
    folder_id = request.args.get("folder", type=int)
    event_id = request.args.get("event", type=int)
    selected_event_date_raw = request.args.get("event_date", "").strip()
    search_query = request.args.get("search", "").strip()
    calendar_year, calendar_month = normalized_calendar_month(request.args.get("calendar_year"), request.args.get("calendar_month"))
    if section not in {"files", "recent", "starred", "trash", "events"}:
        abort(404)
    try:
        selected_event_date = date.fromisoformat(selected_event_date_raw) if selected_event_date_raw else None
    except ValueError:
        selected_event_date = None
    is_event_date_workspace = section == "events" and event_id is None and selected_event_date is not None

    def dashboard_url_with_updates(**updates):
        params = dict(request.args.items())
        if "event_date" in updates:
            updates.setdefault("section", "events")
            updates.setdefault("event", None)
            updates.setdefault("folder", None)
            updates.setdefault("search", None)
        for key, value in updates.items():
            if value in (None, ""):
                params.pop(key, None)
            else:
                params[key] = str(value)
        return url_for("dashboard", **params)

    try:
        current_folder = None
        current_event = None
        breadcrumbs = []
        if event_id is not None:
            if section != "events":
                abort(400)
            current_event = owned_event(event_id)
            if not current_event:
                abort(404)
        if folder_id is not None:
            if section not in {"files", "events"}:
                abort(400)
            current_folder = owned_folder(folder_id)
            if (
                not current_folder
                or (section == "events" and current_folder["event_id"] != event_id)
                or (section != "events" and current_folder["event_id"] is not None)
            ):
                abort(404)
            cursor = get_db().cursor()
            cursor.execute("UPDATE folders SET accessed_at = NOW() WHERE id = %s AND user_id = %s", (folder_id, session["user_id"]))
            get_db().commit()
            cursor.close()
            node = current_folder
            while node:
                if section == "events" and node.get("event_id") != event_id:
                    abort(404)
                if section != "events" and node.get("event_id") is not None:
                    abort(404)
                breadcrumbs.append(node)
                node = owned_folder(node["parent_id"]) if node["parent_id"] else None
            breadcrumbs.reverse()
        cursor = get_db().cursor(dictionary=True)
        cursor.execute("SELECT COALESCE(SUM(file_size), 0) AS total_storage FROM files WHERE user_id = %s AND is_deleted = FALSE", (session["user_id"],))
        total_storage = cursor.fetchone()["total_storage"] or 0
        deleted = section == "trash"
        date_workspace_events = []
        events = []
        if is_event_date_workspace and not search_query:
            cursor.execute(
                "SELECT id, name, event_date, event_type, share_token, created_at, is_starred FROM events "
                "WHERE user_id = %s AND is_deleted = FALSE AND event_date = %s ORDER BY name",
                (session["user_id"], selected_event_date),
            )
            events = cursor.fetchall()
            date_workspace_events = events
            folders = []
            files = []
        elif section == "events" and event_id is None and not search_query:
            cursor.execute("SELECT id, name, event_date, event_type, share_token, created_at, is_starred FROM events WHERE user_id = %s AND is_deleted = FALSE ORDER BY event_date, name", (session["user_id"],))
            events = cursor.fetchall()
            folders = []
            files = []
        elif search_query:
            search_term = f"%{search_query}%"
            folder_scope = []
            if folder_id is not None:
                folder_scope = [folder_id, *folder_descendants(folder_id)]
            if folder_scope:
                placeholders = ",".join(["%s"] * len(folder_scope))
                folder_scope_sql = f" AND id IN ({placeholders})"
                file_scope_sql = f" AND folder_id IN ({placeholders})"
                folder_scope_values = tuple(folder_scope)
            else:
                folder_scope_sql = ""
                file_scope_sql = ""
                folder_scope_values = ()
            if section == "events" and event_id is not None:
                event_scope_sql = " AND event_id = %s"
                event_scope_values = (event_id,)
            elif section == "events":
                event_scope_sql = " AND 1 = 0"
                event_scope_values = ()
            else:
                event_scope_sql = " AND event_id IS NULL"
                event_scope_values = ()
            cursor.execute(
                "SELECT id, name, parent_id, "
                + ("deleted_at, deleted_at AS created_at, " if deleted else "created_at, ")
                + "accessed_at, is_starred, share_token FROM folders "
                f"WHERE user_id = %s AND is_deleted = %s AND name LIKE %s{folder_scope_sql}{event_scope_sql} ORDER BY name",
                (session["user_id"], deleted, search_term, *folder_scope_values, *event_scope_values),
            )
            folders = cursor.fetchall()
            cursor.execute(
                "SELECT id, original_filename, folder_id, file_size, mime_type, "
                + ("deleted_at, deleted_at AS uploaded_at, " if deleted else "uploaded_at, ")
                + "accessed_at, is_starred, share_token FROM files "
                f"WHERE user_id = %s AND is_deleted = %s AND original_filename LIKE %s{file_scope_sql}{event_scope_sql} ORDER BY uploaded_at DESC",
                (session["user_id"], deleted, search_term, *folder_scope_values, *event_scope_values),
            )
            files = cursor.fetchall()
            if section == "events" and event_id is None:
                cursor.execute(
                    "SELECT id, name, event_date, event_type, share_token, created_at, is_starred FROM events "
                    "WHERE user_id = %s AND is_deleted = FALSE AND name LIKE %s ORDER BY name",
                    (session["user_id"], search_term),
                )
                events = cursor.fetchall()
            elif section == "trash":
                cursor.execute(
                    "SELECT id, name, event_date, event_type, share_token, deleted_at, created_at, is_starred FROM events "
                    "WHERE user_id = %s AND is_deleted = TRUE AND name LIKE %s ORDER BY deleted_at DESC",
                    (session["user_id"], search_term),
                )
                events = cursor.fetchall()
        elif section == "starred":
            where = "user_id = %s AND is_deleted = FALSE AND event_id IS NULL AND is_starred = TRUE"
            values = (session["user_id"],)
        elif section == "recent":
            where = "user_id = %s AND is_deleted = FALSE AND event_id IS NULL"
            values = (session["user_id"],)
        elif section == "trash":
            where = "user_id = %s AND is_deleted = TRUE AND event_id IS NULL"
            values = (session["user_id"],)
            cursor.execute(
                "SELECT id, name, event_date, event_type, share_token, deleted_at, created_at, is_starred FROM events "
                "WHERE user_id = %s AND is_deleted = TRUE ORDER BY deleted_at DESC",
                (session["user_id"],),
            )
            events = cursor.fetchall()
        elif is_event_date_workspace:
            where = "user_id = %s AND is_deleted = FALSE AND 1 = 0"
            values = (session["user_id"],)
        elif section == "events":
            where = "user_id = %s AND is_deleted = FALSE AND event_id = %s AND parent_id <=> %s"
            values = (session["user_id"], event_id, folder_id)
        else:
            where = "user_id = %s AND is_deleted = FALSE AND event_id IS NULL AND parent_id <=> %s"
            values = (session["user_id"], folder_id)
        if not search_query and not (section == "events" and event_id is None) and not is_event_date_workspace:
            folder_date = "deleted_at, deleted_at AS created_at" if deleted else "COALESCE(accessed_at, created_at) AS created_at" if section == "recent" else "created_at"
            cursor.execute(f"SELECT id, name, parent_id, share_token, {folder_date}, accessed_at, is_starred FROM folders WHERE {where} ORDER BY created_at DESC", values)
            folders = cursor.fetchall()
        sizes = folder_sizes(cursor, [folder["id"] for folder in folders], include_deleted=deleted)
        for folder in folders:
            folder["size"] = sizes.get(folder["id"], 0)
        event_size_totals = event_sizes(
            cursor,
            [event["id"] for event in events],
            include_deleted=deleted,
            owner_id=session["user_id"],
        )
        for event in events:
            event["size"] = event_size_totals.get(event["id"], 0)
        if not search_query and not (section == "events" and event_id is None) and not is_event_date_workspace:
            file_where = where.replace("parent_id", "folder_id")
            file_date = "deleted_at, deleted_at AS uploaded_at" if deleted else "COALESCE(accessed_at, uploaded_at) AS uploaded_at" if section == "recent" else "uploaded_at"
            cursor.execute(f"SELECT id, original_filename, folder_id, file_size, mime_type, share_token, {file_date}, accessed_at, is_starred FROM files WHERE {file_where} ORDER BY uploaded_at DESC", values)
            files = cursor.fetchall()
        if section == "events" and event_id is not None:
            cursor.execute("SELECT id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id = %s ORDER BY name", (session["user_id"], event_id))
        else:
            cursor.execute("SELECT id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id IS NULL ORDER BY name", (session["user_id"],))
        move_folders = cursor.fetchall()
        cursor.execute("SELECT id, name, event_date, event_type FROM events WHERE user_id = %s AND is_deleted = FALSE ORDER BY event_date, name", (session["user_id"],))
        sidebar_events = cursor.fetchall()
        if section == "events" and event_id is not None:
            cursor.execute("SELECT id, name, parent_id FROM folders WHERE user_id = %s AND event_id = %s", (session["user_id"], event_id))
        else:
            cursor.execute("SELECT id, name, parent_id FROM folders WHERE user_id = %s AND event_id IS NULL", (session["user_id"],))
        paths = folder_paths(cursor.fetchall())
        cursor.close()
        workspace_root_location = (
            display_name(current_event["name"]) if section == "events" and current_event
            else "Events" if section == "events"
            else "Library"
        )
        items = ([{"kind": "folder", "name": item["name"], "date": item["created_at"], "mime_type": "Folder", "location": paths.get(item["parent_id"], workspace_root_location), **item} for item in folders] +
                 [{"kind": "file", "name": item["original_filename"], "parent_id": item["folder_id"], "date": item["uploaded_at"], "location": paths.get(item["folder_id"], workspace_root_location), **item} for item in files] +
                 [{"kind": "event", "parent_id": None, "size": 0, "file_size": 0, "mime_type": "Event", "location": "Events", **item, "date": item["deleted_at"] if deleted else item["created_at"]} for item in (events if (section == "events" and event_id is None) or section == "trash" else [])])
        for item in items:
            location_folder_id = item["parent_id"]
            if deleted:
                item["location_url"] = ""
                item["location_is_current"] = True
            elif location_folder_id is None:
                item["location_url"] = url_for("dashboard", section="events", event=event_id) if section == "events" and event_id is not None else url_for("dashboard", section="events") if section == "events" else url_for("dashboard")
                item["location_is_current"] = section == "events" or (section == "files" and folder_id is None)
            else:
                item["location_url"] = url_for("dashboard", section="events", event=event_id, folder=location_folder_id) if section == "events" and event_id is not None else url_for("dashboard", folder=location_folder_id)
                item["location_is_current"] = folder_id == location_folder_id and section in {"files", "events"}
        calendar_context = build_events_calendar_context(calendar_year, calendar_month, dashboard_url_with_updates)
        page_title = "My Files"
        if current_folder:
            page_title = display_name(current_folder["name"])
        elif current_event:
            page_title = display_name(current_event["name"])
        elif section == "events":
            page_title = "Events"
        elif section == "recent":
            page_title = "Recent"
        elif section == "starred":
            page_title = "Starred"
        elif section == "trash":
            page_title = "Trash"

        return render_template(
            "dashboard.html",
            page_title=page_title,
            items=items,
            total_storage=total_storage,
            total_files=len(date_workspace_events) if is_event_date_workspace and not search_query else len(items),
            section=section,
            current_folder=current_folder,
            breadcrumbs=breadcrumbs,
            folder_id=folder_id,
            event_id=event_id,
            current_event=current_event,
            selected_event_date=selected_event_date,
            selected_event_date_iso=selected_event_date.isoformat() if selected_event_date else "",
            is_event_date_workspace=is_event_date_workspace,
            date_workspace_events=date_workspace_events,
            is_trash=deleted,
            move_folders=move_folders,
            move_destinations=move_destination_options(session["user_id"]),
            sidebar_events=sidebar_events,
            search_query=search_query,
            calendar_auto_open=request.args.get("calendar") == "open",
            is_global_search=bool(search_query),
            is_shared_workspace=False,
            workspace_can_edit=True,
            share_context=None,
            **calendar_context,
        )
    except MySQLError:
        app.logger.exception("Dashboard database error")
        flash("Could not load your files. Please try again.", "error")
        return render_template(
            "dashboard.html",
            page_title="My files",
            items=[],
            total_storage=0,
            total_files=0,
            section="files",
            current_folder=None,
            breadcrumbs=[],
            folder_id=None,
            event_id=None,
            current_event=None,
            selected_event_date=None,
            selected_event_date_iso="",
            is_event_date_workspace=False,
            date_workspace_events=[],
            is_trash=False,
            move_folders=[],
            sidebar_events=[],
            search_query="",
            calendar_auto_open=False,
            is_global_search=False,
            is_shared_workspace=False,
            workspace_can_edit=True,
            share_context=None,
            month_name=calendar_module.month_name[calendar_month],
            year=calendar_year,
            month=calendar_month,
            weeks=sunday_first_month_weeks(calendar_year, calendar_month),
            events_by_day={},
            calendar_previous_url=url_for("dashboard", calendar="open", calendar_year=shift_calendar_month(calendar_year, calendar_month, -1)[0], calendar_month=shift_calendar_month(calendar_year, calendar_month, -1)[1]),
            calendar_next_url=url_for("dashboard", calendar="open", calendar_year=shift_calendar_month(calendar_year, calendar_month, 1)[0], calendar_month=shift_calendar_month(calendar_year, calendar_month, 1)[1]),
            calendar_day_urls={},
        )


@app.get("/search-suggestions")
@login_required
def search_suggestions():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"ok": True, "suggestions": [], "has_more": False})

    section = request.args.get("section", "files")
    folder_id = request.args.get("folder", type=int)
    event_id = request.args.get("event", type=int)
    if section not in {"files", "recent", "starred", "trash", "events"}:
        abort(404)

    deleted = section == "trash"
    owner_id = session["user_id"]
    current_event = None
    if event_id is not None:
        if section != "events":
            abort(400)
        current_event = owned_event(event_id)
        if not current_event:
            abort(404)

    folder_scope = []
    if folder_id is not None:
        current_folder = owned_folder(folder_id, include_deleted=deleted)
        if (
            not current_folder
            or (section == "events" and current_folder.get("event_id") != event_id)
            or (section != "events" and current_folder.get("event_id") is not None)
        ):
            abort(404)
        folder_scope = [folder_id, *folder_descendants(folder_id)]

    search_term = f"%{query}%"
    cursor = get_db().cursor(dictionary=True)
    try:
        if section == "events" and event_id is None:
            cursor.execute(
                "SELECT id, name, event_type FROM events "
                "WHERE user_id = %s AND is_deleted = FALSE AND name LIKE %s "
                "ORDER BY name LIMIT 6",
                (owner_id, search_term),
            )
            matches = [
                {
                    "kind": "event",
                    "name": display_name(item["name"]),
                    "type": event_type_label(item.get("event_type")),
                    "location": "Events",
                    "icon_url": url_for("static", filename=f"images/{event_icon_file(item.get('event_type'))}"),
                    "url": url_for("dashboard", section="events", event=item["id"]),
                }
                for item in cursor.fetchall()
            ]
        else:
            if section == "events":
                event_condition = " AND event_id = %s"
                event_values = (event_id,)
            else:
                event_condition = " AND event_id IS NULL"
                event_values = ()
            if folder_scope:
                placeholders = ",".join(["%s"] * len(folder_scope))
                folder_condition = f" AND id IN ({placeholders})"
                file_condition = f" AND folder_id IN ({placeholders})"
                folder_values = tuple(folder_scope)
            else:
                folder_condition = ""
                file_condition = ""
                folder_values = ()

            cursor.execute(
                "SELECT id, name, parent_id FROM folders "
                f"WHERE user_id = %s AND is_deleted = %s AND name LIKE %s{folder_condition}{event_condition} "
                "ORDER BY name LIMIT 6",
                (owner_id, deleted, search_term, *folder_values, *event_values),
            )
            folders = cursor.fetchall()
            cursor.execute(
                "SELECT id, original_filename, folder_id, mime_type FROM files "
                f"WHERE user_id = %s AND is_deleted = %s AND original_filename LIKE %s{file_condition}{event_condition} "
                "ORDER BY uploaded_at DESC LIMIT 6",
                (owner_id, deleted, search_term, *folder_values, *event_values),
            )
            files = cursor.fetchall()
            cursor.execute(
                "SELECT id, name, parent_id FROM folders "
                f"WHERE user_id = %s AND is_deleted = %s{event_condition}",
                (owner_id, deleted, *event_values),
            )
            paths = folder_paths(cursor.fetchall())
            base_location = display_name(current_event["name"]) if current_event else ("Trash" if deleted else "Library")
            matches = []
            for item in folders:
                matches.append({
                    "kind": "folder",
                    "name": display_name(item["name"]),
                    "type": "Folder",
                    "location": paths.get(item["parent_id"], base_location),
                    "icon_url": url_for("static", filename="images/Folder.png"),
                    "url": url_for("dashboard", section="trash") if deleted else url_for("dashboard", section="events", event=event_id, folder=item["id"]) if section == "events" else url_for("dashboard", folder=item["id"]),
                })
            for item in files:
                if deleted:
                    item_url = url_for("dashboard", section="trash")
                else:
                    parent_workspace_url = (
                        url_for("dashboard", section="events", event=event_id, folder=item["folder_id"])
                        if section == "events" and item["folder_id"] is not None
                        else url_for("dashboard", section="events", event=event_id)
                        if section == "events"
                        else url_for("dashboard", folder=item["folder_id"])
                        if item["folder_id"] is not None
                        else url_for("dashboard")
                    )
                    item_url = url_for("preview", file_id=item["id"], return_to=parent_workspace_url)
                matches.append({
                    "kind": "file",
                    "name": display_name(item["original_filename"]),
                    "type": clean_file_type(item),
                    "location": paths.get(item["folder_id"], base_location),
                    "icon_url": url_for("static", filename=f"images/{file_type_icon(item)}"),
                    "url": item_url,
                })
            if section == "trash" and len(matches) <= 5:
                cursor.execute(
                    "SELECT id, name, event_type FROM events "
                    "WHERE user_id = %s AND is_deleted = TRUE AND name LIKE %s ORDER BY name LIMIT 6",
                    (owner_id, search_term),
                )
                for item in cursor.fetchall():
                    matches.append({
                        "kind": "event",
                        "name": display_name(item["name"]),
                        "type": event_type_label(item.get("event_type")),
                        "location": "Trash",
                        "icon_url": url_for("static", filename=f"images/{event_icon_file(item.get('event_type'))}"),
                        "url": url_for("dashboard", section="trash"),
                    })
    except MySQLError:
        app.logger.exception("Search suggestions database error")
        return jsonify({"ok": False, "error": "Search suggestions are temporarily unavailable."}), 500
    finally:
        cursor.close()

    return jsonify({"ok": True, "suggestions": matches[:5], "has_more": len(matches) > 5})


@app.get("/public-files")
def public_files():
    return public_dashboard()


def public_sidebar_events():
    """Return Events that have an active public-link token for public navigation."""
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, event_date, event_type, share_token FROM events "
            "WHERE is_deleted = FALSE AND share_token IS NOT NULL AND share_token <> '' "
            "ORDER BY event_date DESC, name"
        )
        events = cursor.fetchall()
        for event in events:
            app.logger.info(
                "Public Event sidebar entry: event_id=%s share_token=%s url=%s",
                event["id"],
                event["share_token"],
                url_for("public_event_workspace", event_id=event["id"], share_token=event["share_token"]),
            )
        return events
    except MySQLError:
        app.logger.exception("Public Events sidebar database error")
        return []
    finally:
        cursor.close()


@app.get("/public-events")
def public_events():
    """Render public Events separately from the Public Files workspace."""
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, event_date, event_type, share_token, created_at FROM events "
            "WHERE is_deleted = FALSE AND share_token IS NOT NULL AND share_token <> '' "
            "ORDER BY event_date DESC, name"
        )
        events = cursor.fetchall()
        event_size_totals = event_sizes(cursor, [event["id"] for event in events])
        for event in events:
            event["size"] = event_size_totals.get(event["id"], 0)
    except MySQLError:
        app.logger.exception("Public Events workspace database error")
        abort(500)
    finally:
        cursor.close()

    items = [
        {
            "kind": "event",
            "name": item["name"],
            "parent_id": None,
            "size": item["size"],
            "file_size": 0,
            "mime_type": "Event",
            "location": "Events",
            "date": item["created_at"],
            "accessed_at": None,
            "is_starred": False,
            **item,
        }
        for item in events
    ]
    return render_template(
        "dashboard.html", page_title="Public Events", items=items, total_storage=0, total_files=len(items),
        section="events", current_folder=None, breadcrumbs=[], folder_id=None, event_id=None, current_event=None,
        selected_event_date=None, selected_event_date_iso="", is_event_date_workspace=False,
        date_workspace_events=[], is_trash=False, move_folders=[], sidebar_events=events, search_query="",
        calendar_auto_open=False, is_global_search=False, is_shared_workspace=False, is_public_workspace=True,
        workspace_can_edit=False, share_context=None, public_workspace_kind="events",
        month_name=calendar_module.month_name[date.today().month], year=date.today().year, month=date.today().month,
        weeks=sunday_first_month_weeks(date.today().year, date.today().month), events_by_day={}, calendar_day_urls={},
        calendar_previous_url="", calendar_next_url="", show_calendar_back_link=False,
    )


def public_dashboard():
    """Render active resources with public tokens in a read-only workspace."""
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, share_token, created_at FROM folders "
            "WHERE is_deleted = FALSE AND event_id IS NULL AND share_token IS NOT NULL ORDER BY created_at DESC"
        )
        folders = cursor.fetchall()
        cursor.execute(
            "SELECT id, original_filename, file_size, mime_type, share_token, uploaded_at FROM files "
            "WHERE is_deleted = FALSE AND share_token IS NOT NULL ORDER BY uploaded_at DESC"
        )
        files = cursor.fetchall()
    except MySQLError:
        app.logger.exception("Public workspace database error")
        abort(500)
    finally:
        cursor.close()

    items = (
        [{"kind": "folder", "name": item["name"], "parent_id": None, "size": 0, "file_size": 0,
          "mime_type": "Folder", "location": "Public Files", "date": item["created_at"], "accessed_at": None,
          "is_starred": False, **item} for item in folders]
        + [{"kind": "file", "name": item["original_filename"], "parent_id": None, "folder_id": None,
            "location": "Public Files", "date": item["uploaded_at"], "accessed_at": None, "is_starred": False,
            **item} for item in files]
    )
    return render_template(
        "dashboard.html", page_title="Public Files", items=items, total_storage=0, total_files=len(items),
        section="files", current_folder=None, breadcrumbs=[], folder_id=None, event_id=None, current_event=None,
        selected_event_date=None, selected_event_date_iso="", is_event_date_workspace=False,
        date_workspace_events=[], is_trash=False, move_folders=[], sidebar_events=public_sidebar_events(), search_query="",
        calendar_auto_open=False, is_global_search=False, is_shared_workspace=False, is_public_workspace=True,
        workspace_can_edit=False, share_context=None, public_workspace_kind="files",
        month_name=calendar_module.month_name[date.today().month], year=date.today().year, month=date.today().month,
        weeks=sunday_first_month_weeks(date.today().year, date.today().month), events_by_day={}, calendar_day_urls={},
        calendar_previous_url="", calendar_next_url="", show_calendar_back_link=False,
    )


@app.get("/events/calendar")
@login_required
def events_calendar():
    calendar_year, calendar_month = normalized_calendar_month(request.args.get("calendar_year"), request.args.get("calendar_month"))
    def calendar_url_with_updates(**updates):
        params = dict(request.args.items())
        for key, value in updates.items():
            if value in (None, ""):
                params.pop(key, None)
            else:
                params[key] = str(value)
        return url_for("events_calendar", **params)
    calendar_context = build_events_calendar_context(calendar_year, calendar_month, calendar_url_with_updates)
    calendar_context["calendar_day_urls"] = {
        day: url_for(
            "dashboard",
            section="events",
            event_date=date(calendar_year, calendar_month, day).isoformat(),
            calendar_year=calendar_year,
            calendar_month=calendar_month,
        )
        for day in calendar_context["calendar_day_urls"]
    }
    return render_template("events_calendar.html", **calendar_context)


@app.post("/upload")
@login_required
def upload():
    share_context = request_share_context()
    raw_folder_id = request.form.get("folder_id")
    raw_event_id = request.form.get("event_id")
    if share_context:
        if raw_folder_id in (None, "", "root"):
            folder_id = None
        elif not str(raw_folder_id).isdigit():
            abort(400)
        else:
            folder_id = int(raw_folder_id)
        target_folder = accessible_folder(folder_id, require_owner=True, share_context=share_context) if folder_id else None
        if raw_folder_id not in (None, "", "root") and not target_folder:
            abort(404)
        upload_owner_id = share_context["owner_id"]
        if share_context["kind"] == "event":
            target_event = accessible_event(share_context["item_id"], require_owner=True, share_context=share_context)
            if not target_event:
                abort(404)
            event_id = target_event["id"]
            if raw_event_id not in (None, "") and (not str(raw_event_id).isdigit() or int(raw_event_id) != event_id):
                abort(400)
            if target_folder and target_folder.get("event_id") != event_id:
                abort(400)
        else:
            event_id = target_folder.get("event_id") if target_folder else None
            if raw_event_id not in (None, "") and (not str(raw_event_id).isdigit() or int(raw_event_id) != event_id):
                abort(400)
    else:
        folder_id = valid_destination(raw_folder_id)
        upload_owner_id = session["user_id"]
        target_folder = owned_folder(folder_id) if folder_id else None
        event_id = valid_event(raw_event_id)
        if target_folder:
            folder_event_id = target_folder.get("event_id")
            if event_id is not None and folder_event_id != event_id:
                abort(400)
            event_id = folder_event_id

    if share_context and share_context["kind"] == "event":
        upload_return_url = url_for("public_event", share_token=share_context["token"], folder=folder_id) if folder_id else url_for("public_event", share_token=share_context["token"])
    elif share_context and share_context["kind"] == "folder":
        upload_return_url = url_for("public_folder", share_token=share_context["token"], folder=folder_id) if folder_id else url_for("public_folder", share_token=share_context["token"])
    elif event_id is not None:
        upload_return_url = url_for("dashboard", section="events", event=event_id, folder=folder_id) if folder_id else url_for("dashboard", section="events", event=event_id)
    else:
        upload_return_url = url_for("dashboard", folder=folder_id) if folder_id else url_for("dashboard")
    incoming_files = request.files.getlist("file")
    folder_paths = request.form.getlist("folder_path")
    valid_files = [item for item in incoming_files if item and item.filename]
    if not valid_files:
        flash("Select a file to upload.", "error")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "results": [{"name": "", "status": "error", "message": "Select a file to upload."}]})
        return redirect_to_workspace(upload_return_url)

    user_folder = user_directory(upload_owner_id)
    user_folder.mkdir(parents=True, exist_ok=True)

    uploaded = 0
    results = []
    folder_cache = {}

    def upload_target_folder(relative_path):
        if not relative_path:
            return folder_id
        parts = [part for part in relative_path.replace("\\", "/").split("/") if part]
        if len(parts) < 2:
            return folder_id

        parent_id = folder_id
        path_parts = []
        for part in parts[:-1]:
            safe_part = secure_filename(part).strip("._")
            if not safe_part or safe_part in {".", ".."}:
                raise ValueError("The selected folder path is invalid.")
            path_parts.append(safe_part)
            cache_key = (parent_id, *path_parts)
            if cache_key not in folder_cache:
                cursor = get_db().cursor()
                try:
                    cursor.execute(
                        "SELECT id FROM folders WHERE user_id = %s AND parent_id <=> %s AND event_id <=> %s "
                        "AND name = %s AND is_deleted = FALSE ORDER BY id LIMIT 1",
                        (upload_owner_id, parent_id, event_id, safe_part),
                    )
                    existing_folder = cursor.fetchone()
                    if existing_folder:
                        folder_cache[cache_key] = existing_folder[0]
                    else:
                        cursor.execute(
                            "INSERT INTO folders (user_id, parent_id, event_id, name, share_token) VALUES (%s, %s, %s, %s, %s)",
                            (upload_owner_id, parent_id, event_id, safe_part, secrets.token_urlsafe(32)),
                        )
                        folder_cache[cache_key] = cursor.lastrowid
                        get_db().commit()
                except MySQLError:
                    get_db().rollback()
                    raise
                finally:
                    cursor.close()
            parent_id = folder_cache[cache_key]
        return parent_id

    for index, incoming in enumerate(incoming_files):
        if incoming is None or not incoming.filename:
            results.append({"name": "", "status": "error", "message": "No file selected."})
            continue

        original_name = secure_filename(incoming.filename)
        if not original_name:
            results.append({"name": incoming.filename, "status": "error", "message": "The selected filename is invalid."})
            continue

        incoming.stream.seek(0, os.SEEK_END)
        file_size = incoming.stream.tell()
        incoming.stream.seek(0)
        if file_size <= 0:
            results.append({"name": original_name, "status": "error", "message": "Empty files cannot be uploaded."})
            continue
        if file_size > MAX_FILE_SIZE_BYTES:
            results.append({"name": original_name, "status": "error", "message": f"Files must be {MAX_FILE_SIZE_MB} MB or smaller."})
            continue

        try:
            target_folder_id = upload_target_folder(folder_paths[index] if index < len(folder_paths) else "")
        except (MySQLError, ValueError):
            app.logger.exception("Upload folder path error")
            results.append({"name": original_name, "status": "error", "message": "The folder could not be created for this upload."})
            continue

        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        share_token = secrets.token_urlsafe(32)
        destination = user_folder / stored_name
        try:
            incoming.save(destination)
        except OSError:
            app.logger.exception("File save error")
            results.append({"name": original_name, "status": "error", "message": "The file could not be saved. Please try again."})
            continue

        cursor = None
        try:
            cursor = get_db().cursor()
            cursor.execute(
                "INSERT INTO files (user_id, original_filename, stored_filename, file_size, mime_type, share_token, folder_id, event_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    upload_owner_id,
                    original_name,
                    stored_name,
                    file_size,
                    incoming.mimetype or "application/octet-stream",
                    share_token,
                    target_folder_id,
                    event_id,
                ),
            )
            get_db().commit()
            uploaded += 1
            results.append({"name": original_name, "status": "success", "message": "File uploaded successfully."})
        except MySQLError:
            get_db().rollback()
            app.logger.exception("Upload metadata database error")
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                app.logger.exception("Could not remove orphaned upload")
            results.append({"name": original_name, "status": "error", "message": "The upload could not be completed. Please try again."})
        finally:
            if cursor:
                cursor.close()

    if uploaded:
        flash(f"{uploaded} file(s) uploaded successfully.", "success")
    else:
        flash("No valid files were uploaded.", "error")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": uploaded > 0, "uploaded": uploaded, "results": results})
    return redirect_to_workspace(upload_return_url)


@app.get("/download/<int:file_id>")
@login_or_public_link_required
def download(file_id):
    share_context = request_share_context()
    try:
        record = accessible_file(file_id, share_context=share_context)
    except MySQLError:
        app.logger.exception("Download database error")
        abort(500)
    if not record:
        abort(404)
    directory = user_directory(record["user_id"])
    path = record_path(record)
    if not path.is_file():
        flash("This file is no longer available on the server.", "error")
        return redirect(workspace_return_url())
    return send_from_directory(directory, record["stored_filename"], as_attachment=True, download_name=record["original_filename"])


@app.get("/download/folder/<int:folder_id>")
@login_or_public_link_required
def download_folder(folder_id):
    share_context = request_share_context()
    try:
        folder = accessible_folder(folder_id, share_context=share_context)
        if not folder:
            abort(404)

        folder_ids = [folder_id, *folder_descendants(folder_id, owner_id=folder["user_id"])]
        placeholders = ",".join(["%s"] * len(folder_ids))
        cursor = get_db().cursor(dictionary=True)
        try:
            cursor.execute(
                f"SELECT id, parent_id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND id IN ({placeholders})",
                (folder["user_id"], *folder_ids),
            )
            folders = cursor.fetchall()
            cursor.execute(
                f"SELECT stored_filename, original_filename, folder_id FROM files WHERE user_id = %s AND is_deleted = FALSE AND folder_id IN ({placeholders})",
                (folder["user_id"], *folder_ids),
            )
            files = cursor.fetchall()
        finally:
            cursor.close()

        relative_paths = {folder_id: folder["name"]}
        pending = [folder_id]
        while pending:
            parent_id = pending.pop()
            for child in folders:
                if child["parent_id"] == parent_id:
                    relative_paths[child["id"]] = f"{relative_paths[parent_id]}/{child['name']}"
                    pending.append(child["id"])

        archive = BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for item in folders:
                bundle.writestr(f"{relative_paths[item['id']]}/", "")
            owner_directory = user_directory(folder["user_id"])
            for item in files:
                path = owner_directory / item["stored_filename"]
                if path.is_file() and item["folder_id"] in relative_paths:
                    bundle.write(path, arcname=f"{relative_paths[item['folder_id']]}/{item['original_filename']}")

        archive.seek(0)
        return send_file(
            archive,
            as_attachment=True,
            download_name=f"{folder['name']}.zip",
            mimetype="application/zip",
        )
    except MySQLError:
        app.logger.exception("Folder download database error")
        abort(500)


@app.get("/download/event/<int:event_id>")
@login_or_public_link_required
def download_event(event_id):
    share_context = request_share_context()
    event = accessible_event(event_id, share_context=share_context)
    if not event:
        abort(404)
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        write_event_archive(bundle, event)
    archive.seek(0)
    return send_file(
        archive,
        as_attachment=True,
        download_name=f"{event['name']}.zip",
        mimetype="application/zip",
    )


@app.get("/offline-manifest/<kind>/<int:item_id>")
@login_or_public_link_required
def offline_manifest(kind, item_id):
    if kind not in {"file", "folder", "event"}:
        abort(404)

    share_context = request_share_context()
    context_params = {}
    if share_context:
        context_params = {
            "share_context_kind": share_context["kind"],
            "share_context_token": share_context["token"],
        }

    files = []
    folders = []
    root = None
    if kind == "file":
        root = accessible_file(item_id, share_context=share_context)
        if root:
            files = [root]
    elif kind == "folder":
        root = accessible_folder(item_id, share_context=share_context)
        if root:
            folder_ids = [item_id, *folder_descendants(item_id, owner_id=root["user_id"])]
            placeholders = ",".join(["%s"] * len(folder_ids))
            cursor = get_db().cursor(dictionary=True)
            try:
                cursor.execute(
                    f"SELECT id, parent_id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND id IN ({placeholders})",
                    (root["user_id"], *folder_ids),
                )
                folders = cursor.fetchall()
                cursor.execute(
                    f"SELECT * FROM files WHERE user_id = %s AND is_deleted = FALSE AND folder_id IN ({placeholders})",
                    (root["user_id"], *folder_ids),
                )
                files = cursor.fetchall()
            finally:
                cursor.close()
    else:
        root = accessible_event(item_id, share_context=share_context)
        if root:
            cursor = get_db().cursor(dictionary=True)
            try:
                cursor.execute(
                    "SELECT id, parent_id, name FROM folders WHERE user_id = %s AND event_id = %s AND is_deleted = FALSE",
                    (root["user_id"], item_id),
                )
                folders = cursor.fetchall()
                cursor.execute(
                    "SELECT * FROM files WHERE user_id = %s AND event_id = %s AND is_deleted = FALSE",
                    (root["user_id"], item_id),
                )
                files = cursor.fetchall()
            finally:
                cursor.close()

    if not root:
        abort(404)

    urls = [
        url_for("static", filename="css/style.css"),
        url_for("static", filename="js/app.js"),
        url_for("static", filename="images/JF.ico"),
        url_for("static", filename="images/JF.png"),
        url_for("static", filename="images/ss.png"),
    ]
    if folders:
        urls.append(url_for("static", filename="images/Folder.png"))
    urls.extend(url_for("static", filename=f"images/{file_type_icon(file_record)}") for file_record in files)
    if kind == "event":
        urls.append(url_for("static", filename=f"images/{event_icon_file(root.get('event_type'))}"))

    root_open_url = ""
    root_download_url = ""
    if kind == "file":
        root_open_url = url_for("preview", file_id=item_id, **context_params)
        root_download_url = url_for("download", file_id=item_id, **context_params)
        urls.append(root_open_url)
    elif kind == "folder":
        root_download_url = url_for("download_folder", folder_id=item_id, **context_params)
        if share_context and share_context["kind"] == "event":
            root_open_url = url_for("public_event", share_token=share_context["token"], folder=item_id)
            urls.append(root_open_url)
            urls.extend(url_for("public_event", share_token=share_context["token"], folder=folder["id"]) for folder in folders if folder["id"] != item_id)
        elif share_context:
            root_open_url = url_for("public_folder", share_token=share_context["token"])
            urls.append(root_open_url)
            urls.extend(url_for("public_folder", share_token=share_context["token"], folder=folder["id"]) for folder in folders if folder["id"] != item_id)
        else:
            root_open_url = url_for("dashboard", folder=item_id)
            urls.append(root_open_url)
            urls.extend(url_for("dashboard", folder=folder["id"]) for folder in folders if folder["id"] != item_id)
    else:
        root_download_url = url_for("download_event", event_id=item_id, **context_params)
        if share_context:
            root_open_url = url_for("public_event", share_token=share_context["token"])
            urls.append(root_open_url)
            urls.extend(url_for("public_event", share_token=share_context["token"], folder=folder["id"]) for folder in folders)
        else:
            root_open_url = url_for("dashboard", section="events", event=item_id)
            urls.append(root_open_url)
            urls.extend(url_for("dashboard", section="events", event=item_id, folder=folder["id"]) for folder in folders)

    for file_record in files:
        file_id = file_record["id"]
        urls.extend([
            url_for("preview", file_id=file_id, **context_params),
            url_for("preview_content", file_id=file_id, **context_params),
            url_for("download", file_id=file_id, **context_params),
        ])
        if preview_kind(file_record) == "powerpoint":
            urls.append(url_for("presentation_preview_manifest", file_id=file_id, **context_params))
            try:
                _cache_directory, presentation_manifest = render_presentation_preview(file_record)
                urls.extend(
                    url_for("presentation_preview_slide", file_id=file_id, slide_number=index, **context_params)
                    for index in range(1, presentation_manifest["slide_count"] + 1)
                )
            except PresentationPreviewError:
                app.logger.warning("Presentation %s could not be added to the offline preview cache", file_id)

    # Cache the root download as well as its browsable contents so both the
    # table action and the overflow menu continue to work without a network.
    urls.append(root_download_url)

    # Offline listings always show the item's original creation timestamp:
    # uploaded_at for files and created_at for folders/events. Do not derive
    # this value from access time, scheduled event date, or cache time.
    item_date = root.get("uploaded_at") if kind == "file" else root.get("created_at")
    item_type = clean_file_type(root) if kind == "file" else "Folder" if kind == "folder" else event_type_label(root.get("event_type"))
    item_size = int(root.get("file_size") or 0) if kind == "file" else sum(int(file_record.get("file_size") or 0) for file_record in files)

    preview_kinds = {preview_kind(file_record) for file_record in files}
    if "spreadsheet" in preview_kinds:
        urls.append("https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js")

    return jsonify({
        "ok": True,
        "item": {
            "kind": kind,
            "id": item_id,
            "name": root.get("original_filename") if kind == "file" else root.get("name"),
        },
        "open_url": root_open_url,
        "download_url": root_download_url,
        "file_count": len(files),
        "details": {
            "type": item_type,
            "date": format_datetime(item_date),
            "size": item_size,
            "location": "Saved Files Offline",
        },
        "urls": list(dict.fromkeys(urls)),
    })


@app.get("/service-worker.js")
def service_worker():
    response = send_from_directory(app.static_folder, "js/service-worker.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/preview/<int:file_id>")
def preview(file_id):
    share_context = request_share_context()
    try:
        record = accessible_file(file_id, share_context=share_context)
    except MySQLError:
        app.logger.exception("Preview database error")
        abort(500)
    if not record:
        abort(404)
    is_public_workspace = "user_id" not in session
    if not is_public_workspace:
        cursor = get_db().cursor()
        try:
            cursor.execute("UPDATE files SET accessed_at = NOW() WHERE id = %s AND user_id = %s", (file_id, record["user_id"]))
            get_db().commit()
        finally:
            cursor.close()
    cursor = get_db().cursor(dictionary=True)
    try:
        if record.get("event_id") is not None:
            cursor.execute("SELECT id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id = %s ORDER BY name", (record["user_id"], record["event_id"]))
        else:
            cursor.execute("SELECT id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id IS NULL ORDER BY name", (record["user_id"],))
        move_folders = cursor.fetchall()
    finally:
        cursor.close()
    return render_template(
        "preview.html",
        file=record,
        preview_kind=preview_kind(record),
        move_folders=move_folders,
        move_destinations=move_destination_options(record["user_id"]) if record["can_edit"] else [],
        workspace_return_url=workspace_return_url(),
        file_location="Public Files" if is_public_workspace else file_location(record),
        workspace_can_edit=record["can_edit"],
        is_public_workspace=is_public_workspace,
        share_context=share_context,
    )


@app.get("/file/<share_token>")
def token_preview(share_token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,64}", share_token):
        abort(404)
    try:
        share_context = share_context_from_token("file", share_token)
        record = accessible_file(share_context["item_id"], share_context=share_context) if share_context else None
    except MySQLError:
        app.logger.exception("Token preview database error")
        abort(500)
    if not record:
        abort(404)
    is_public_workspace = "user_id" not in session
    move_folders = []
    if not is_public_workspace:
        cursor = get_db().cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id IS NULL ORDER BY name", (record["user_id"],))
            move_folders = cursor.fetchall()
        finally:
            cursor.close()
    return render_template(
        "preview.html",
        file=record,
        preview_kind=preview_kind(record),
        move_folders=move_folders,
        move_destinations=move_destination_options(record["user_id"]) if record["can_edit"] else [],
        workspace_return_url=workspace_return_url(),
        file_location="Public Files" if is_public_workspace else file_location(record),
        workspace_can_edit=record["can_edit"],
        is_public_workspace=is_public_workspace,
        share_context=share_context,
    )


@app.get("/preview-content/<int:file_id>")
def preview_content(file_id):
    share_context = request_share_context()
    try:
        record = accessible_file(file_id, share_context=share_context)
    except MySQLError:
        app.logger.exception("Preview content database error")
        abort(500)
    if not record:
        abort(404)
    path = record_path(record)
    if not path.is_file():
        abort(404)
    response = send_from_directory(
        user_directory(record["user_id"]),
        record["stored_filename"],
        as_attachment=False,
        mimetype=record["mime_type"],
        download_name=record["original_filename"],
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "sandbox"
    return response


@app.get("/presentation-preview/<int:file_id>/manifest")
@login_or_public_link_required
def presentation_preview_manifest(file_id):
    share_context = request_share_context()
    try:
        record = accessible_file(file_id, share_context=share_context)
    except MySQLError:
        app.logger.exception("Presentation preview database error")
        return jsonify({"ok": False, "error": "The presentation preview is temporarily unavailable."}), 500
    if not record or preview_kind(record) != "powerpoint":
        abort(404)
    try:
        _cache_directory, manifest = render_presentation_preview(record)
    except PresentationPreviewError as error:
        return jsonify({"ok": False, "error": str(error)}), 503
    params = presentation_share_params(share_context)
    step_names = manifest.get("steps") or [[name] for name in manifest["slides"]]
    return jsonify({
        "ok": True,
        "slide_count": manifest["slide_count"],
        "width": manifest["width"],
        "height": manifest["height"],
        "pages": manifest.get("pages", []),
        "dpi": manifest.get("dpi"),
        "renderer": manifest.get("renderer", "libreoffice-pdf"),
        "animation_mode": manifest.get("animation_mode", "static-final-frame"),
        "animation_sequences": manifest.get("animation_sequences", {}),
        "slides": [
            url_for("presentation_preview_slide", file_id=file_id, slide_number=index, **params)
            for index in range(1, manifest["slide_count"] + 1)
        ],
        "steps": [
            [
                url_for(
                    "presentation_preview_step",
                    file_id=file_id,
                    slide_number=slide_index,
                    step_number=step_index,
                    **params,
                )
                for step_index in range(len(slide_steps))
            ]
            for slide_index, slide_steps in enumerate(step_names, start=1)
        ],
    })


@app.get("/presentation-preview/<int:file_id>/slide/<int:slide_number>")
@login_or_public_link_required
def presentation_preview_slide(file_id, slide_number):
    share_context = request_share_context()
    try:
        record = accessible_file(file_id, share_context=share_context)
    except MySQLError:
        app.logger.exception("Presentation slide database error")
        abort(500)
    if not record or preview_kind(record) != "powerpoint":
        abort(404)
    try:
        cache_directory, manifest = render_presentation_preview(record)
    except PresentationPreviewError:
        abort(503)
    if slide_number < 1 or slide_number > manifest["slide_count"]:
        abort(404)
    response = send_from_directory(
        cache_directory,
        manifest["slides"][slide_number - 1],
        mimetype="image/png",
        conditional=True,
        max_age=86400,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/presentation-preview/<int:file_id>/slide/<int:slide_number>/step/<int:step_number>")
@login_or_public_link_required
def presentation_preview_step(file_id, slide_number, step_number):
    share_context = request_share_context()
    try:
        record = accessible_file(file_id, share_context=share_context)
    except MySQLError:
        app.logger.exception("Presentation animation frame database error")
        abort(500)
    if not record or preview_kind(record) != "powerpoint":
        abort(404)
    try:
        cache_directory, manifest = render_presentation_preview(record)
    except PresentationPreviewError:
        abort(503)
    step_groups = manifest.get("steps") or [[name] for name in manifest.get("slides", [])]
    if slide_number < 1 or slide_number > len(step_groups):
        abort(404)
    slide_steps = step_groups[slide_number - 1]
    if step_number < 0 or step_number >= len(slide_steps):
        abort(404)
    response = send_from_directory(
        cache_directory,
        slide_steps[step_number],
        mimetype="image/png",
        conditional=True,
        max_age=86400,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/view/<int:file_id>")
@login_required
def view_file(file_id):
    share_context = request_share_context()
    try:
        record = accessible_file(file_id, share_context=share_context)
    except MySQLError:
        app.logger.exception("File view database error")
        abort(500)
    if not record:
        abort(404)
    directory = user_directory(record["user_id"])
    path = directory / record["stored_filename"]
    if not path.is_file():
        flash("This file is no longer available on the server.", "error")
        return redirect(url_for("dashboard"))
    return send_from_directory(directory, record["stored_filename"], as_attachment=False, download_name=record["original_filename"])


@app.post("/delete/<int:file_id>")
@login_required
def delete(file_id):
    try:
        record = owned_file(file_id)
        if not record:
            flash("File not found or access denied.", "error")
            return redirect_to_workspace()
        cursor = get_db().cursor()
        cursor.execute("UPDATE files SET original_folder_id = folder_id, is_deleted = TRUE, deleted_at = NOW() WHERE id = %s AND user_id = %s", (file_id, session["user_id"]))
        get_db().commit()
        cursor.close()
        flash("File moved to Trash.", "danger")
    except MySQLError:
        get_db().rollback()
        app.logger.exception("File deletion error")
        flash("The file could not be moved to Trash. Please try again.", "error")
    return redirect_to_workspace()


@app.post("/folders")
@login_required
def create_folder():
    name = secure_filename(request.form.get("name", "")).strip("._")
    parent_id = valid_destination(request.form.get("parent_id"))
    parent_folder = owned_folder(parent_id) if parent_id else None
    event_id = valid_event(request.form.get("event_id"))
    if parent_folder:
        parent_event_id = parent_folder.get("event_id")
        if event_id is not None and parent_event_id != event_id:
            abort(400)
        event_id = parent_event_id
    if not name:
        flash("Enter a valid folder name.", "error")
    else:
        cursor = get_db().cursor()
        try:
            cursor.execute(
                "INSERT INTO folders (user_id, parent_id, event_id, name, share_token) VALUES (%s, %s, %s, %s, %s)",
                (session["user_id"], parent_id, event_id, name, secrets.token_urlsafe(32)),
            )
            get_db().commit()
            flash("Folder created.", "success")
        except MySQLError:
            get_db().rollback()
            flash("The folder could not be created.", "error")
        finally:
            cursor.close()
    if event_id is not None:
        default_url = url_for("dashboard", section="events", event=event_id, folder=parent_id) if parent_id else url_for("dashboard", section="events", event=event_id)
    else:
        default_url = url_for("dashboard", folder=parent_id) if parent_id else url_for("dashboard")
    return redirect_to_workspace(default_url)


@app.post("/events")
@login_required
def create_event():
    name = secure_filename(request.form.get("name", "")).strip("._")
    raw_date = request.form.get("event_date", "")
    event_type = (request.form.get("event_type") or "event").strip().lower()
    try:
        event_date = date.fromisoformat(raw_date)
    except ValueError:
        event_date = None
    if event_type not in EVENT_TYPE_FILE_MAP:
        event_type = "event"
    if not name or not event_date:
        flash("Enter a valid Event name and date.", "error")
        return redirect_to_workspace(url_for("dashboard", section="events"))
    cursor = get_db().cursor()
    try:
        cursor.execute(
            "INSERT INTO events (user_id, name, event_date, event_type, share_token) VALUES (%s, %s, %s, %s, %s)",
            (session["user_id"], name, event_date, event_type, secrets.token_urlsafe(32)),
        )
        get_db().commit()
        flash("Event created.", "success")
    except MySQLError:
        get_db().rollback()
        app.logger.exception("Event creation error")
        flash("The Event could not be created.", "error")
    finally:
        cursor.close()
    return redirect_to_workspace(url_for("dashboard", section="events"))


@app.post("/rename")
@login_required
def rename_item():
    share_context = request_share_context()
    kind = request.form.get("kind", "")
    raw_id = request.form.get("item_id", "")
    name = request.form.get("name", "").strip()
    if kind not in {"file", "folder"} or not raw_id.isdigit() or not name:
        abort(400)
    safe_name = secure_filename(name).strip("._")
    if not safe_name:
        flash("Enter a valid name.", "error")
        return redirect_to_workspace()
    table = "files" if kind == "file" else "folders"
    column = "original_filename" if kind == "file" else "name"
    if kind == "file":
        record = accessible_file(int(raw_id), require_owner=True, share_context=share_context)
        if not record:
            abort(404)
        original_extension = Path(record["original_filename"]).suffix
        submitted_extension = Path(safe_name).suffix
        if submitted_extension and submitted_extension.lower() != original_extension.lower():
            flash("A file's extension cannot be changed.", "error")
            return redirect_to_workspace()
        if original_extension:
            safe_name = f"{safe_name[:-len(submitted_extension)] if submitted_extension else safe_name}{original_extension}"
    else:
        record = accessible_folder(int(raw_id), require_owner=True, share_context=share_context)
        if not record:
            abort(404)
    cursor = get_db().cursor()
    try:
        cursor.execute(
            f"UPDATE {table} SET {column} = %s WHERE id = %s AND user_id = %s AND is_deleted = FALSE",
            (safe_name, int(raw_id), record["user_id"]),
        )
        if cursor.rowcount != 1:
            abort(404)
        get_db().commit()
        flash("Item renamed.", "success")
    except MySQLError:
        get_db().rollback()
        app.logger.exception("Rename error")
        flash("The item could not be renamed.", "error")
    finally:
        cursor.close()
    return redirect_to_workspace()


@app.post("/events/update")
@login_required
def update_event():
    raw_id = request.form.get("item_id", "")
    name = request.form.get("name", "").strip()
    if not raw_id.isdigit() or not name:
        abort(400)
    safe_name = secure_filename(name).strip("._")
    if not safe_name:
        flash("Enter a valid Event title.", "error")
        return redirect_to_workspace(url_for("dashboard", section="events"))
    event = owned_event(int(raw_id))
    if not event:
        abort(404)
    event_type = (request.form.get("event_type") or "event").strip().lower()
    if event_type not in EVENT_TYPE_FILE_MAP:
        event_type = "event"
    cursor = get_db().cursor()
    try:
        cursor.execute(
            "UPDATE events SET name = %s, event_type = %s WHERE id = %s AND user_id = %s AND is_deleted = FALSE",
            (safe_name, event_type, int(raw_id), session["user_id"]),
        )
        if cursor.rowcount != 1:
            abort(404)
        get_db().commit()
        flash("Event updated.", "success")
    except MySQLError:
        get_db().rollback()
        app.logger.exception("Event update error")
        flash("The Event could not be updated.", "error")
    finally:
        cursor.close()
    return redirect_to_workspace()


@app.post("/items/star")
@login_required
def star_items():
    selected = request.form.getlist("items")
    starred = request.form.get("starred") == "true"
    for item in selected:
        kind, _, raw_id = item.partition(":")
        if kind not in {"file", "folder", "event"} or not raw_id.isdigit():
            abort(400)
        table = "files" if kind == "file" else "folders" if kind == "folder" else "events"
        cursor = get_db().cursor()
        try:
            cursor.execute(f"UPDATE {table} SET is_starred = %s WHERE id = %s AND user_id = %s AND is_deleted = FALSE", (starred, int(raw_id), session["user_id"]))
            get_db().commit()
        finally:
            cursor.close()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})
    flash("Items added to Starred." if starred else "Items removed from Starred.", "success")
    return redirect_to_workspace()


@app.post("/items/move")
@login_required
def move_items():
    """Move Library items using the existing Library move workflow."""
    share_context = request_share_context()
    raw_destination = request.form.get("destination_id")
    destination_event_id = None
    if raw_destination in (None, "", "root", "library"):
        destination = None
    elif raw_destination and raw_destination.startswith("event:"):
        raw_event_id = raw_destination.partition(":")[2]
        if not raw_event_id.isdigit():
            abort(400)
        destination_event = owned_event(int(raw_event_id))
        if not destination_event:
            abort(404)
        destination = None
        destination_event_id = destination_event["id"]
    elif raw_destination and raw_destination.startswith("folder:"):
        raw_folder_id = raw_destination.partition(":")[2]
        if not raw_folder_id.isdigit():
            abort(400)
        destination_folder = accessible_folder(int(raw_folder_id), require_owner=True, share_context=share_context)
        if not destination_folder:
            abort(404)
        destination = destination_folder["id"]
        destination_event_id = destination_folder.get("event_id")
    elif str(raw_destination).isdigit():
        destination_folder = accessible_folder(int(raw_destination), require_owner=True, share_context=share_context)
        if not destination_folder:
            abort(404)
        destination = destination_folder["id"]
        destination_event_id = destination_folder.get("event_id")
    else:
        abort(400)

    operations = []
    for item in request.form.getlist("items"):
        kind, _, raw_id = item.partition(":")
        if kind not in {"file", "folder"} or not raw_id.isdigit():
            abort(400)
        item_id = int(raw_id)
        if kind == "folder":
            folder = accessible_folder(item_id, require_owner=True, share_context=share_context)
            if not folder:
                abort(404)
            if folder.get("event_id") is not None:
                abort(400)
            descendants = folder_descendants(item_id, owner_id=folder["user_id"])
            if destination == item_id or (destination and destination in descendants):
                abort(400)
            if folder.get("parent_id") == destination and destination_event_id is None:
                abort(400)
            operations.append((kind, folder, [item_id, *descendants]))
        else:
            file_record = accessible_file(item_id, require_owner=True, share_context=share_context)
            if not file_record:
                abort(404)
            if file_record.get("event_id") is not None:
                abort(400)
            if file_record.get("folder_id") == destination and destination_event_id is None:
                abort(400)
            operations.append((kind, file_record, None))

    cursor = get_db().cursor()
    try:
        for kind, record, subtree_ids in operations:
            if kind == "file":
                cursor.execute(
                    "UPDATE files SET folder_id = %s, event_id = %s "
                    "WHERE id = %s AND user_id = %s AND is_deleted = FALSE",
                    (destination, destination_event_id, record["id"], record["user_id"]),
                )
            else:
                placeholders = ",".join(["%s"] * len(subtree_ids))
                cursor.execute(
                    "UPDATE folders SET parent_id = %s, event_id = %s "
                    "WHERE id = %s AND user_id = %s AND is_deleted = FALSE",
                    (destination, destination_event_id, record["id"], record["user_id"]),
                )
                cursor.execute(
                    f"UPDATE folders SET event_id = %s WHERE user_id = %s AND is_deleted = FALSE AND id IN ({placeholders})",
                    (destination_event_id, record["user_id"], *subtree_ids),
                )
                cursor.execute(
                    f"UPDATE files SET event_id = %s WHERE user_id = %s AND is_deleted = FALSE AND folder_id IN ({placeholders})",
                    (destination_event_id, record["user_id"], *subtree_ids),
                )
        get_db().commit()
    except MySQLError:
        get_db().rollback()
        raise
    finally:
        cursor.close()
    flash("Items moved to the selected destination.", "success")
    return redirect_to_workspace()


@app.post("/events/items/move")
@login_required
def move_event_items():
    """Move Event files/folders only to a different Event workspace."""
    share_context = request_share_context()
    raw_source_event_id = request.form.get("source_event_id", "")
    if not raw_source_event_id.isdigit():
        abort(400)
    source_event = owned_event(int(raw_source_event_id))
    if not source_event:
        abort(404)
    source_event_id = source_event["id"]
    raw_destination = request.form.get("destination_id", "")
    destination_folder = None
    if raw_destination.startswith("event:"):
        raw_event_id = raw_destination.partition(":")[2]
        if not raw_event_id.isdigit():
            abort(400)
        destination_event = owned_event(int(raw_event_id))
        if not destination_event:
            abort(404)
        destination = None
        destination_event_id = destination_event["id"]
    elif raw_destination.startswith("folder:"):
        raw_folder_id = raw_destination.partition(":")[2]
        if not raw_folder_id.isdigit():
            abort(400)
        destination_folder = accessible_folder(int(raw_folder_id), require_owner=True, share_context=share_context)
        if not destination_folder:
            abort(404)
        destination_event_id = destination_folder.get("event_id")
        if destination_event_id is None or not owned_event(destination_event_id):
            abort(400)
        destination = destination_folder["id"]
    else:
        # Library roots and Library folders are never valid Event destinations.
        abort(400)

    operations = []
    for item in request.form.getlist("items"):
        kind, _, raw_id = item.partition(":")
        if kind not in {"file", "folder"} or not raw_id.isdigit():
            abort(400)
        item_id = int(raw_id)
        if kind == "folder":
            record = accessible_folder(item_id, require_owner=True, share_context=share_context)
            if not record:
                abort(404)
            if record.get("event_id") != source_event_id or source_event_id == destination_event_id:
                abort(400)
            descendants = folder_descendants(item_id, owner_id=record["user_id"])
            if destination == item_id or (destination and destination in descendants):
                abort(400)
            operations.append((kind, record, [item_id, *descendants]))
        else:
            record = accessible_file(item_id, require_owner=True, share_context=share_context)
            if not record:
                abort(404)
            if record.get("event_id") != source_event_id or source_event_id == destination_event_id:
                abort(400)
            operations.append((kind, record, None))

    cursor = get_db().cursor()
    try:
        for kind, record, subtree_ids in operations:
            if kind == "file":
                cursor.execute(
                    "UPDATE files SET folder_id = %s, event_id = %s "
                    "WHERE id = %s AND user_id = %s AND is_deleted = FALSE",
                    (destination, destination_event_id, record["id"], record["user_id"]),
                )
                continue
            placeholders = ",".join(["%s"] * len(subtree_ids))
            cursor.execute(
                "UPDATE folders SET parent_id = %s, event_id = %s "
                "WHERE id = %s AND user_id = %s AND is_deleted = FALSE",
                (destination, destination_event_id, record["id"], record["user_id"]),
            )
            cursor.execute(
                f"UPDATE folders SET event_id = %s WHERE user_id = %s AND is_deleted = FALSE AND id IN ({placeholders})",
                (destination_event_id, record["user_id"], *subtree_ids),
            )
            cursor.execute(
                f"UPDATE files SET event_id = %s WHERE user_id = %s AND is_deleted = FALSE AND folder_id IN ({placeholders})",
                (destination_event_id, record["user_id"], *subtree_ids),
            )
        get_db().commit()
    except MySQLError:
        get_db().rollback()
        raise
    finally:
        cursor.close()
    flash("Event items moved to the selected Event.", "success")
    return redirect_to_workspace()


def selected_items_from_form(include_deleted=False):
    selected = []
    for item in request.form.getlist("items"):
        kind, _, raw_id = item.partition(":")
        if kind not in {"file", "folder", "event"} or not raw_id.isdigit():
            abort(400)
        table = "files" if kind == "file" else "folders" if kind == "folder" else "events"
        deleted_condition = "" if include_deleted else " AND is_deleted = FALSE"
        record = query_one(f"SELECT * FROM {table} WHERE id = %s AND user_id = %s{deleted_condition}", (int(raw_id), session["user_id"]))
        if not record:
            abort(404)
        selected.append((kind, int(raw_id), record))
    return selected


@app.post("/items/trash")
@login_required
def trash_items():
    for kind, item_id, _record in selected_items_from_form():
        cursor = get_db().cursor()
        try:
            if kind == "event":
                cursor.execute("UPDATE events SET is_deleted = TRUE, deleted_at = NOW() WHERE id = %s AND user_id = %s", (item_id, session["user_id"]))
                cursor.execute(
                    "UPDATE folders SET original_parent_id = parent_id, is_deleted = TRUE, deleted_at = NOW() "
                    "WHERE user_id = %s AND event_id = %s AND is_deleted = FALSE",
                    (session["user_id"], item_id),
                )
                cursor.execute(
                    "UPDATE files SET original_folder_id = folder_id, is_deleted = TRUE, deleted_at = NOW() "
                    "WHERE user_id = %s AND event_id = %s AND is_deleted = FALSE",
                    (session["user_id"], item_id),
                )
            else:
                table = "files" if kind == "file" else "folders"
                location_column = "folder_id" if kind == "file" else "parent_id"
                original_column = "original_folder_id" if kind == "file" else "original_parent_id"
                cursor.execute(
                    f"UPDATE {table} SET {original_column} = {location_column}, is_deleted = TRUE, deleted_at = NOW() "
                    "WHERE id = %s AND user_id = %s",
                    (item_id, session["user_id"]),
                )
            if kind == "folder":
                descendants = folder_descendants(item_id)
                if descendants:
                    placeholders = ",".join(["%s"] * len(descendants))
                    cursor.execute(f"UPDATE folders SET is_deleted = TRUE, deleted_at = NOW() WHERE user_id = %s AND id IN ({placeholders})", (session["user_id"], *descendants))
                    cursor.execute(f"UPDATE files SET is_deleted = TRUE, deleted_at = NOW() WHERE user_id = %s AND folder_id IN ({placeholders})", (session["user_id"], *descendants))
                cursor.execute("UPDATE files SET is_deleted = TRUE, deleted_at = NOW() WHERE user_id = %s AND folder_id = %s", (session["user_id"], item_id))
            get_db().commit()
        finally:
            cursor.close()
    flash("Selected items moved to Trash.", "danger")
    return redirect_to_workspace()


@app.post("/items/restore")
@login_required
def restore_items():
    for kind, item_id, record in selected_items_from_form(include_deleted=True):
        if not record["is_deleted"]:
            continue
        cursor = get_db().cursor()
        try:
            if kind == "event":
                cursor.execute("UPDATE events SET is_deleted = FALSE, deleted_at = NULL WHERE id = %s AND user_id = %s", (item_id, session["user_id"]))
                cursor.execute("UPDATE folders SET is_deleted = FALSE, deleted_at = NULL WHERE user_id = %s AND event_id = %s", (session["user_id"], item_id))
                cursor.execute("UPDATE files SET is_deleted = FALSE, deleted_at = NULL WHERE user_id = %s AND event_id = %s", (session["user_id"], item_id))
            elif kind == "folder":
                original = record.get("original_parent_id")
                target = original if original and owned_folder(original) else None
                folder_ids = [item_id, *folder_descendants(item_id, include_deleted=True)]
                placeholders = ",".join(["%s"] * len(folder_ids))
                cursor.execute("UPDATE folders SET parent_id = %s, is_deleted = FALSE, deleted_at = NULL WHERE id = %s AND user_id = %s", (target, item_id, session["user_id"]))
                cursor.execute(f"UPDATE folders SET is_deleted = FALSE, deleted_at = NULL WHERE user_id = %s AND id IN ({placeholders})", (session["user_id"], *folder_ids))
                cursor.execute(f"UPDATE files SET is_deleted = FALSE, deleted_at = NULL WHERE user_id = %s AND folder_id IN ({placeholders})", (session["user_id"], *folder_ids))
            else:
                original = record.get("original_folder_id")
                target = original if original and owned_folder(original) else None
                cursor.execute("UPDATE files SET folder_id = %s, is_deleted = FALSE, deleted_at = NULL WHERE id = %s AND user_id = %s", (target, item_id, session["user_id"]))
            get_db().commit()
        finally:
            cursor.close()
    flash("Selected items restored from Trash.", "success")
    return redirect_to_workspace(url_for("dashboard", section="trash"))


@app.post("/items/permanent-delete")
@login_required
def permanent_delete_items():
    for kind, item_id, record in selected_items_from_form(include_deleted=True):
        if not record["is_deleted"]:
            abort(400)
        cursor = get_db().cursor(dictionary=True)
        try:
            if kind == "event":
                permanently_delete_event_record(cursor, record)
            elif kind == "folder":
                permanently_delete_folder_record(cursor, record)
            else:
                permanently_delete_file_record(cursor, record)
            get_db().commit()
        finally:
            cursor.close()
    flash("Selected items permanently deleted.", "danger")
    return redirect_to_workspace(url_for("dashboard", section="trash"))


@app.post("/trash/empty")
@login_required
def empty_trash():
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, user_id, name FROM events WHERE user_id = %s AND is_deleted = TRUE", (session["user_id"],))
        for event in cursor.fetchall():
            permanently_delete_event_record(cursor, event)
        cursor.execute("SELECT id, user_id, name FROM folders WHERE user_id = %s AND is_deleted = TRUE ORDER BY id", (session["user_id"],))
        deleted_folder_ids = set()
        for folder in cursor.fetchall():
            if folder["id"] in deleted_folder_ids:
                continue
            subtree_ids = [folder["id"], *folder_descendants(folder["id"], owner_id=session["user_id"], include_deleted=True)]
            permanently_delete_folder_record(cursor, folder)
            deleted_folder_ids.update(subtree_ids)
        cursor.execute("SELECT id, user_id, stored_filename FROM files WHERE user_id = %s AND is_deleted = TRUE", (session["user_id"],))
        for record in cursor.fetchall():
            permanently_delete_file_record(cursor, record)
        get_db().commit()
    except (MySQLError, OSError):
        get_db().rollback()
        app.logger.exception("Empty Trash error")
        flash("Trash could not be emptied. Please try again.", "error")
        return redirect(url_for("dashboard", section="trash"))
    finally:
        cursor.close()
    flash("Trash emptied.", "danger")
    return redirect(url_for("dashboard", section="trash"))


@app.post("/items/download")
@login_required
def bulk_download():
    selected = selected_items_from_form()
    if not selected:
        abort(400)
    if len(selected) == 1 and selected[0][0] == "file":
        return redirect(url_for("download", file_id=selected[0][1]))
    if len(selected) == 1 and selected[0][0] == "event":
        return redirect(url_for("download_event", event_id=selected[0][1]))

    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        user_directory = UPLOAD_FOLDER / str(session["user_id"])
        written_paths = set()

        def unique_archive_path(path):
            candidate = path
            counter = 2
            while candidate in written_paths:
                stem, suffix = os.path.splitext(path)
                candidate = f"{stem} ({counter}){suffix}"
                counter += 1
            written_paths.add(candidate)
            return candidate

        for kind, _item_id, record in selected:
            if kind != "file":
                continue
            path = UPLOAD_FOLDER / str(session["user_id"]) / record["stored_filename"]
            if path.is_file():
                bundle.write(path, arcname=unique_archive_path(record["original_filename"]))

        for kind, _event_id, event in selected:
            if kind != "event":
                continue
            write_event_archive(bundle, event, written_paths)

        for kind, folder_id, folder in selected:
            if kind != "folder":
                continue
            folder_ids = [folder_id, *folder_descendants(folder_id, owner_id=folder["user_id"])]
            placeholders = ",".join(["%s"] * len(folder_ids))
            cursor = get_db().cursor(dictionary=True)
            try:
                cursor.execute(
                    f"SELECT id, parent_id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND id IN ({placeholders})",
                    (session["user_id"], *folder_ids),
                )
                folders = cursor.fetchall()
                cursor.execute(
                    f"SELECT stored_filename, original_filename, folder_id FROM files WHERE user_id = %s AND is_deleted = FALSE AND folder_id IN ({placeholders})",
                    (session["user_id"], *folder_ids),
                )
                files = cursor.fetchall()
            finally:
                cursor.close()

            relative_paths = {folder_id: folder["name"]}
            pending = [folder_id]
            while pending:
                parent_id = pending.pop()
                for child in folders:
                    if child["parent_id"] == parent_id:
                        relative_paths[child["id"]] = f"{relative_paths[parent_id]}/{child['name']}"
                        pending.append(child["id"])

            for item in folders:
                if item["id"] in relative_paths:
                    directory_path = f"{relative_paths[item['id']]}/"
                    if directory_path not in written_paths:
                        written_paths.add(directory_path)
                        bundle.writestr(directory_path, "")
            for item in files:
                path = user_directory / item["stored_filename"]
                if path.is_file() and item["folder_id"] in relative_paths:
                    archive_path = f"{relative_paths[item['folder_id']]}/{item['original_filename']}"
                    bundle.write(path, arcname=unique_archive_path(archive_path))
    archive.seek(0)
    return send_file(archive, as_attachment=True, download_name="jfcmpila-files.zip", mimetype="application/zip")


@app.get("/folder/<share_token>")
def public_folder(share_token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,64}", share_token):
        abort(404)
    share_context = share_context_from_token("folder", share_token)
    if not share_context:
        abort(404)
    current_folder_id = request.args.get("folder", type=int) or share_context["item_id"]
    current_folder = accessible_folder(current_folder_id, share_context=share_context)
    if not current_folder or current_folder.get("event_id") is not None:
        abort(404)

    breadcrumbs = []
    node = current_folder
    while node:
        breadcrumbs.append(node)
        if node["id"] == share_context["item_id"] or not node["parent_id"]:
            break
        node = folder_record(node["parent_id"])
    breadcrumbs.reverse()

    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, parent_id, created_at, accessed_at, is_starred, share_token FROM folders "
            "WHERE user_id = %s AND is_deleted = FALSE AND event_id IS NULL AND parent_id <=> %s ORDER BY created_at DESC",
            (share_context["owner_id"], current_folder_id),
        )
        folders = [folder for folder in cursor.fetchall() if folder_is_within(folder["id"], share_context["item_id"])]
        sizes = folder_sizes(cursor, [folder["id"] for folder in folders], include_deleted=False, owner_id=share_context["owner_id"])
        for folder in folders:
            folder["size"] = sizes.get(folder["id"], 0)
        cursor.execute(
            "SELECT id, user_id, original_filename, folder_id, file_size, mime_type, uploaded_at, accessed_at, is_starred, share_token "
            "FROM files WHERE user_id = %s AND is_deleted = FALSE AND event_id IS NULL AND folder_id <=> %s ORDER BY uploaded_at DESC",
            (share_context["owner_id"], current_folder_id),
        )
        files = cursor.fetchall()
        cursor.execute("SELECT id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id IS NULL ORDER BY name", (share_context["owner_id"],))
        move_folders = [folder for folder in cursor.fetchall() if folder["id"] == share_context["item_id"] or folder_is_within(folder["id"], share_context["item_id"])]
        cursor.execute("SELECT id, name, parent_id FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id IS NULL", (share_context["owner_id"],))
        paths = folder_paths(cursor.fetchall())
    finally:
        cursor.close()

    items = (
        [{"kind": "folder", "name": item["name"], "date": item["created_at"], "mime_type": "Folder", "location": paths.get(item["parent_id"], "Library"), **item} for item in folders]
        + [{"kind": "file", "name": item["original_filename"], "parent_id": item["folder_id"], "date": item["uploaded_at"], "location": paths.get(item["folder_id"], "Library"), **item} for item in files]
    )
    for item in items:
        item["location_url"] = ""
        item["location_is_current"] = True

    return render_template(
        "dashboard.html",
        page_title=display_name(current_folder["name"]),
        items=items,
        total_storage=0,
        total_files=len(items),
        section="files",
        current_folder=current_folder,
        breadcrumbs=breadcrumbs,
        folder_id=current_folder_id,
        event_id=None,
        current_event=None,
        is_trash=False,
        move_folders=[] if "user_id" not in session else move_folders,
        move_destinations=move_destination_options(session["user_id"]) if "user_id" in session else [],
        sidebar_events=public_sidebar_events(),
        search_query="",
        is_global_search=False,
        is_shared_workspace=True,
        workspace_can_edit=share_context["can_edit"],
        is_public_workspace="user_id" not in session,
        share_context=share_context,
        shared_root_folder_id=share_context["item_id"],
        public_workspace_kind="files",
    )


def public_event_context(event_id, share_token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", share_token or ""):
        return None
    record = query_one(
        "SELECT id, user_id, share_token FROM events "
        "WHERE id = %s AND share_token = %s AND is_deleted = FALSE",
        (event_id, share_token),
    )
    app.logger.info(
        "Public Event database lookup: event_id=%s share_token=%s result=%s",
        event_id,
        share_token,
        {"id": record["id"], "user_id": record["user_id"], "token_present": bool(record["share_token"])} if record else None,
    )
    if not record:
        return None
    return {
        "kind": "event",
        "token": record["share_token"],
        "item_id": record["id"],
        "owner_id": record["user_id"],
        "can_edit": False,
    }


@app.get("/public-events/<int:event_id>/<share_token>")
def public_event_workspace(event_id, share_token):
    app.logger.info(
        "Public Event request: event_id=%s share_token=%s path=%s authenticated=%s",
        event_id,
        share_token,
        request.path,
        "user_id" in session,
    )
    share_context = public_event_context(event_id, share_token)
    if not share_context:
        abort(404)
    return render_public_event_workspace(event_id, share_context)


@app.get("/event/<share_token>")
def public_event(share_token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", share_token):
        abort(404)
    share_context = share_context_from_token("event", share_token)
    if not share_context:
        abort(404)
    share_context = {**share_context, "can_edit": False}
    event_id = share_context["item_id"]
    return render_public_event_workspace(event_id, share_context)


def render_public_event_workspace(event_id, share_context):
    current_event = event_record(event_id)
    if not current_event or current_event["user_id"] != share_context["owner_id"] or current_event["id"] != share_context["item_id"]:
        abort(404)
    current_event = {**current_event, "can_edit": False, "access_via": "event_link"}
    current_folder_id = request.args.get("folder", type=int)
    current_folder = None
    breadcrumbs = []
    if current_folder_id is not None:
        current_folder = accessible_folder(current_folder_id, share_context=share_context)
        if not current_folder or current_folder.get("event_id") != event_id:
            abort(404)
        node = current_folder
        while node:
            if node.get("event_id") != event_id or node.get("user_id") != share_context["owner_id"]:
                abort(404)
            breadcrumbs.append(node)
            node = folder_record(node["parent_id"]) if node["parent_id"] else None
        breadcrumbs.reverse()

    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, parent_id, event_id, created_at, accessed_at, is_starred, share_token "
            "FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id = %s AND parent_id <=> %s ORDER BY created_at DESC",
            (share_context["owner_id"], event_id, current_folder_id),
        )
        folders = cursor.fetchall()
        sizes = folder_sizes(cursor, [folder["id"] for folder in folders], include_deleted=False, owner_id=share_context["owner_id"])
        for folder in folders:
            folder["size"] = sizes.get(folder["id"], 0)
        cursor.execute(
            "SELECT id, user_id, original_filename, folder_id, event_id, file_size, mime_type, uploaded_at, accessed_at, is_starred, share_token "
            "FROM files WHERE user_id = %s AND is_deleted = FALSE AND event_id = %s AND folder_id <=> %s ORDER BY uploaded_at DESC",
            (share_context["owner_id"], event_id, current_folder_id),
        )
        files = cursor.fetchall()
        app.logger.info(
            "Public Event scoped content: event_id=%s owner_id=%s folder_id=%s folders=%d files=%d path=%s",
            event_id,
            share_context["owner_id"],
            current_folder_id,
            len(folders),
            len(files),
            request.path,
        )
        cursor.execute("SELECT id, name FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id = %s ORDER BY name", (share_context["owner_id"], event_id))
        move_folders = [folder for folder in cursor.fetchall() if accessible_folder(folder["id"], require_owner=True, share_context=share_context)]
        cursor.execute("SELECT id, name, parent_id FROM folders WHERE user_id = %s AND is_deleted = FALSE AND event_id = %s", (share_context["owner_id"], event_id))
        paths = folder_paths(cursor.fetchall())
    finally:
        cursor.close()

    event_location = display_name(current_event["name"])
    items = (
        [{"kind": "folder", "name": item["name"], "date": item["created_at"], "mime_type": "Folder", "location": paths.get(item["parent_id"], event_location), **item} for item in folders]
        + [{"kind": "file", "name": item["original_filename"], "parent_id": item["folder_id"], "date": item["uploaded_at"], "location": paths.get(item["folder_id"], event_location), **item} for item in files]
    )
    for item in items:
        item["location_url"] = ""
        item["location_is_current"] = True

    return render_template(
        "dashboard.html",
        page_title=display_name(current_folder["name"] if current_folder else current_event["name"]),
        items=items,
        total_storage=0,
        total_files=len(items),
        section="events",
        current_folder=current_folder,
        breadcrumbs=breadcrumbs,
        folder_id=current_folder_id,
        event_id=event_id,
        current_event=current_event,
        selected_event_date=None,
        selected_event_date_iso="",
        is_event_date_workspace=False,
        date_workspace_events=[],
        is_trash=False,
        move_folders=[] if "user_id" not in session else move_folders,
        move_destinations=move_destination_options(session["user_id"]) if "user_id" in session else [],
        sidebar_events=public_sidebar_events(),
        search_query="",
        calendar_auto_open=False,
        is_global_search=False,
        is_shared_workspace=True,
        workspace_can_edit=share_context["can_edit"],
        is_public_workspace=not share_context["can_edit"],
        share_context=share_context,
        public_workspace_kind="events",
        month_name=calendar_module.month_name[date.today().month],
        year=date.today().year,
        month=date.today().month,
        weeks=sunday_first_month_weeks(date.today().year, date.today().month),
        events_by_day={},
        calendar_previous_url=None,
        calendar_next_url=None,
        calendar_day_urls={},
    )


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "ok": False,
            "uploaded": 0,
            "results": [{"name": "", "status": "error", "message": f"Files must be {MAX_FILE_SIZE_MB} MB or smaller."}],
        }), 413
    flash(f"Files must be {MAX_FILE_SIZE_MB} MB or smaller.", "error")
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", message="The requested page or file was not found."), 404


@app.errorhandler(500)
def server_error(_error):
    original_error = getattr(_error, "original_exception", None)
    if original_error:
        app.logger.error(
            "Unhandled server exception for path=%s",
            request.path,
            exc_info=(type(original_error), original_error, original_error.__traceback__),
        )
    else:
        app.logger.error("Server error response for path=%s: %s", request.path, _error)
    return render_template("error.html", message="Something went wrong. Please try again later."), 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
