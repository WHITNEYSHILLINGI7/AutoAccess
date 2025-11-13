from __future__ import annotations

from pathlib import Path
from typing import Tuple, Callable, Any
import json

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
import pandas as pd
import os

from config import UPLOADS_DIR, USERS_JSON, DB_PATH, EMAIL_LOG, SAMPLE_XLSX
from database import init_db, fetch_recent_users, log_event, create_notification, fetch_user_notifications, mark_notification_read, get_unread_notification_count
from autoaccess import ensure_initial_files, process_file
from simulate_ad import SimulatedAD
from email_simulator import send_email_simulated
import secrets


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("AUTOACCESS_SECRET_KEY", "autoaccess-demo-secret")
    app.config["UPLOAD_FOLDER"] = str(UPLOADS_DIR)

    ensure_initial_files()
    init_db(DB_PATH)

    # Auth helpers
    def login_required(view_func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            if not session.get("is_admin"):
                flash("Please log in as admin to continue.", "error")
                return redirect(url_for("login", next=request.path))
            return view_func(*args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return wrapper

    def employee_required(view_func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            if not session.get("is_employee"):
                flash("Please log in to the Employee Portal.", "error")
                return redirect(url_for("employee_login"))
            return view_func(*args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return wrapper

    def employee_has_permission(required_permission: str) -> bool:
        email = session.get("emp_email")
        if not email:
            return False
        ad = SimulatedAD()
        for u in ad.list_users():
            if u.get("email", "").lower() == email.lower():
                perms = u.get("permissions") or []
                return required_permission in perms
        return False

    @app.context_processor
    def inject_employee():
        """Expose a helper in templates to check employee permissions."""
        return dict(emp_can=employee_has_permission)

    @app.route("/")
    def landing():
        return render_template("landing.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        users_df = _read_users_df()
        audit_rows = fetch_recent_users(limit=100)
        users_count = int(len(users_df))
        emails_sent = sum(1 for r in audit_rows if r[1] == "email_sent")
        deactivated = sum(1 for r in audit_rows if r[1] == "deactivate_user")
        last_processed = max((r[0] for r in audit_rows), default="—")
        return render_template(
            "index.html",
            users=users_df.to_dict(orient="records"),
            users_count=users_count,
            emails_sent=emails_sent,
            deactivated=deactivated,
            last_processed=last_processed,
        )

    @app.route("/upload", methods=["GET", "POST"])
    @login_required
    def upload():
        if request.method == "POST":
            file = request.files.get("file")
            if not file or file.filename == "":
                flash("No file selected", "error")
                return redirect(request.url)
            # Support .xlsx or .csv
            ext = ".xlsx" if file.filename.lower().endswith(".xlsx") else ".csv"
            save_path = UPLOADS_DIR / f"new_hires{ext}"
            file.save(str(save_path))
            created, deactivated, errors = process_file(save_path)

            # Send in-app notification to admin if there are errors
            if errors > 0:
                try:
                    admin_notification_id = create_notification(
                        "system",
                        "admin@company.com",  # Admin email
                        f"File Validation Errors: {errors} issues found",
                        f"The uploaded file '{file.filename}' contains {errors} validation errors. Please review the errors in the dashboard and correct the data before re-processing."
                    )
                    print(f"Admin in-app notification created: {admin_notification_id}")
                except Exception as e:
                    print(f"Failed to create admin notification: {e}")

            flash(f"Processed: {created} created, {deactivated} deactivated, {errors} errors", "success")
            return redirect(url_for("dashboard"))
        return render_template("upload.html")

    @app.route("/download/sample")
    @login_required
    def download_sample():
        return send_from_directory(UPLOADS_DIR, "new_hires.xlsx", as_attachment=True)

    @app.route("/users/<username>/edit", methods=["GET", "POST"])
    @login_required
    def edit_user(username: str):
        ad = SimulatedAD()
        user = ad.get_user(username)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            updates = {
                "name": request.form.get("name", user["name"]),
                "email": request.form.get("email", user["email"]),
                "department": request.form.get("department", user["department"]),
                "role": request.form.get("role", user["role"]),
                "status": request.form.get("status", user["status"]),
            }
            try:
                ad.update_user(username, updates)
                from database import log_event
                log_event("update_user", username, f"dept={updates['department']} role={updates['role']} status={updates['status']}")
                flash("User updated successfully.", "success")
                return redirect(url_for("dashboard"))
            except Exception as e:
                flash(f"Update failed: {e}", "error")
        return render_template("user_edit.html", user=user)

    @app.route("/users/<username>/notify", methods=["GET", "POST"])
    @login_required
    def notify_user(username: str):
        ad = SimulatedAD()
        user = ad.get_user(username)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            subject = request.form.get("subject", "").strip()
            body = request.form.get("body", "").strip()
            if not subject or not body:
                flash("Subject and body are required.", "error")
                return render_template("user_notify.html", user=user)
            try:
                send_email_simulated(user["email"], subject, body)
                log_event("admin_notify", username, f"to={user['email']}")
                flash("Notification sent.", "success")
                return redirect(url_for("dashboard"))
            except Exception as e:
                flash(f"Failed to send: {e}", "error")
        return render_template("user_notify.html", user=user)

    @app.route("/users/<username>/deactivate", methods=["POST"])
    @login_required
    def deactivate_user(username: str):
        ad = SimulatedAD()
        user = ad.get_user(username)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("dashboard"))
        if user.get("status") == "inactive":
            flash("User is already deactivated.", "error")
            return redirect(url_for("dashboard"))
        try:
            ad.deactivate_user(username)
            log_event("admin_deactivate", username, "deactivated by admin")
            flash(f"User {username} has been deactivated successfully.", "success")
        except Exception as e:
            flash(f"Deactivation failed: {e}", "error")
        return redirect(url_for("dashboard"))

    @app.route("/notifications", methods=["GET", "POST"])
    @login_required
    def notifications():
        if request.method == "POST":
            recipient_email = request.form.get("recipient_email", "").strip()
            subject = request.form.get("subject", "").strip()
            message = request.form.get("message", "").strip()

            if not recipient_email or not subject or not message:
                flash("All fields are required.", "error")
                return redirect(request.url)

            # Verify recipient exists
            ad = SimulatedAD()
            recipient = None
            for u in ad.list_users():
                if u.get("email", "").lower() == recipient_email.lower():
                    recipient = u
                    break

            if not recipient:
                flash("Recipient not found.", "error")
                return redirect(request.url)

            try:
                notification_id = create_notification("admin", recipient_email, subject, message)
                log_event("send_notification", recipient.get("username"), f"to={recipient_email} id={notification_id}")
                flash("Notification sent successfully.", "success")
                return redirect(url_for("notifications"))
            except Exception as e:
                flash(f"Failed to send notification: {e}", "error")

        # GET request - show form and recent notifications
        ad = SimulatedAD()
        users = [u for u in ad.list_users() if u.get("status") == "active"]
        return render_template("notifications.html", users=users)

    # Employee OTP Login
    @app.route("/employee/login", methods=["GET", "POST"])
    def employee_login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            # Lookup user by email
            ad = SimulatedAD()
            target = None
            for u in ad.list_users():
                if u.get("email", "").lower() == email and u.get("status") == "active":
                    target = u
                    break
            if not target:
                flash("No active user found with that email.", "error")
                return render_template("employee_login.html")
            # Generate OTP and "send" via email
            otp = str(secrets.randbelow(900000) + 100000)
            session["emp_email"] = email
            session["emp_otp"] = otp
            send_email_simulated(email, "Your AutoAccess Login Code", f"Your one-time code is: {otp}\nThis code expires when the browser session ends.")
            flash("A login code has been sent to your email.", "success")
            return redirect(url_for("employee_verify"))
        return render_template("employee_login.html")

    @app.route("/employee/verify", methods=["GET", "POST"])
    def employee_verify():
        email = session.get("emp_email")
        if not email:
            return redirect(url_for("employee_login"))
        if request.method == "POST":
            code = request.form.get("code", "").strip()
            if code and code == session.get("emp_otp"):
                session["is_employee"] = True
                flash("Logged in.", "success")
                return redirect(url_for("employee_dashboard"))
            flash("Invalid code.", "error")
        return render_template("employee_verify.html", email=email)

    @app.route("/employee/dashboard")
    @employee_required
    def employee_dashboard():
        email = session.get("emp_email")
        if not email:
            return redirect(url_for("employee_login"))
        ad = SimulatedAD()
        me = None
        for u in ad.list_users():
            if u.get("email", "").lower() == email:
                me = u
                break
        if not me:
            flash("Your account could not be found.", "error")
            return redirect(url_for("employee_login"))
        if me.get("status") != "active":
            flash("Your account is not active.", "error")
            return redirect(url_for("employee_logout"))

        # Get unread notification count for the quick actions badge
        unread_count = get_unread_notification_count(email)

        return render_template("employee_dashboard.html", user=me, unread_count=unread_count)

    @app.route("/employee/notifications")
    @employee_required
    def employee_notifications():
        email = session.get("emp_email")
        if not email:
            return redirect(url_for("employee_login"))

        # Fetch notifications for this user
        notifications_data = fetch_user_notifications(email)
        notifications = []
        for row in notifications_data:
            # Parse and format the timestamp
            from datetime import datetime
            try:
                # Parse ISO format timestamp
                dt = datetime.fromisoformat(row[1].replace('Z', '+00:00'))
                formatted_time = dt.strftime('%b %d, %Y %I:%M %p')
            except:
                formatted_time = row[1]  # Fallback to raw timestamp

            notifications.append({
                'id': row[0],
                'created_at': row[1],
                'formatted_time': formatted_time,
                'sender_username': row[2],
                'subject': row[3],
                'message': row[4],
                'is_read': bool(row[5])
            })

        unread_count = get_unread_notification_count(email)

        return render_template("employee_notifications.html", notifications=notifications, unread_count=unread_count)

    @app.route("/employee/mark-notification-read/<int:notification_id>", methods=["POST"])
    @employee_required
    def mark_notification_read(notification_id: int):
        email = session.get("emp_email")
        if not email:
            return {"success": False, "error": "Not authenticated"}, 401

        success = mark_notification_read(notification_id, email)
        return {"success": success}

    @app.route("/employee/logout")
    def employee_logout():
        session.pop("is_employee", None)
        session.pop("emp_email", None)
        session.pop("emp_otp", None)
        flash("Logged out.", "success")
        return redirect(url_for("landing"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            admin_user = os.environ.get("AUTOACCESS_ADMIN_USER", "admin")
            admin_pass = os.environ.get("AUTOACCESS_ADMIN_PASS", "admin123!")
            if username == admin_user and password == admin_pass:
                # Clear any employee session when elevating to admin
                session.pop("is_employee", None)
                session.pop("emp_email", None)
                session.pop("emp_otp", None)
                session["is_admin"] = True
                flash("Logged in successfully.", "success")
                next_url = request.args.get("next") or url_for("dashboard")
                return redirect(next_url)
            flash("Invalid credentials.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out.", "success")
        return redirect(url_for("landing"))

    return app


def _read_users_df() -> pd.DataFrame:
    if not USERS_JSON.exists():
        return pd.DataFrame(columns=["username", "name", "email", "department", "role", "status", "created_at"])
    try:
        data = json.loads(USERS_JSON.read_text(encoding="utf-8"))
        return pd.DataFrame(data.get("users", []))
    except Exception:
        return pd.DataFrame(columns=["username", "name", "email", "department", "role", "status", "created_at"])


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


