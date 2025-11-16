from __future__ import annotations

from pathlib import Path
from typing import Tuple, Callable, Any
import json

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
import pandas as pd
import os

from config import UPLOADS_DIR, USERS_JSON, DB_PATH, EMAIL_LOG, SAMPLE_XLSX, API_ENABLED, API_RATE_LIMIT_REQUESTS, API_RATE_LIMIT_WINDOW, ROLE_ACCESS_MATRIX, OU_BY_DEPARTMENT
from database import init_db, fetch_recent_users, log_event, create_notification, fetch_user_notifications, mark_notification_read, get_unread_notification_count, fetch_errors
from autoaccess import ensure_initial_files, process_file
from simulate_ad import SimulatedAD, ADUser
from email_simulator import send_email_simulated
from api_auth import api_key_required, rate_limit
import secrets
from datetime import datetime
from dateutil.parser import parse as parse_date
from autoaccess import username_from_email
from flask import jsonify
from dataclasses import asdict


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

    @app.route("/clear_users", methods=["POST"])
    @login_required
    def clear_users():
        try:
            ad = SimulatedAD()
            ad.clear_all_users()
            log_event("clear_all_users", None, "all users cleared by admin")
            flash("All users have been cleared successfully.", "success")
        except Exception as e:
            flash(f"Failed to clear users: {e}", "error")
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
            
            # Attempt to send OTP email
            email_sent = send_email_simulated(
                email, 
                "Your AutoAccess Login Code", 
                f"Your one-time code is: {otp}\n\nThis code expires when the browser session ends.\n\nIf you did not request this code, please ignore this email."
            )
            
            if email_sent:
                flash("A login code has been sent to your email.", "success")
                return redirect(url_for("employee_verify"))
            else:
                # Email sending failed
                from database import log_error
                import os
                log_error("otp_email_failed", f"Failed to send OTP email to {email}. OTP was generated but not sent.", None)
                
                # In development/simulation mode, show helpful message
                # In production, this would just say "email not configured"
                use_real_email = os.environ.get("USE_REAL_EMAIL", "false").lower() == "true"
                if not use_real_email:
                    flash(
                        f"⚠ Email simulation mode: OTP was generated but not sent. "
                        f"To enable real emails, set USE_REAL_EMAIL=true. "
                        f"Check server logs for OTP: {otp}",
                        "error"
                    )
                else:
                    flash(
                        "⚠ Failed to send email. Please contact support or check your email configuration. "
                        "The OTP has been logged on the server.",
                        "error"
                    )
                # Still redirect to verify page - OTP is in session
                # Admin can check logs if needed, or configure email properly
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

    # API Routes - only if API is enabled
    if API_ENABLED:
        @app.route("/api/users", methods=["GET"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_get_users():
            """Get all users with optional filtering."""
            ad = SimulatedAD()
            users = ad.list_users()

            # Apply filters
            status_filter = request.args.get("status")
            department_filter = request.args.get("department")

            if status_filter:
                users = [u for u in users if u.get("status") == status_filter]
            if department_filter:
                users = [u for u in users if u.get("department") == department_filter]

            return jsonify({
                "success": True,
                "count": len(users),
                "users": users
            })

        @app.route("/api/users/<username>", methods=["GET"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_get_user(username: str):
            """Get a specific user."""
            ad = SimulatedAD()
            user = ad.get_user(username)
            if not user:
                return jsonify({
                    "success": False,
                    "error": "User not found"
                }), 404

            return jsonify({
                "success": True,
                "user": user
            })

        @app.route("/api/users", methods=["POST"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_create_user():
            """Create a new user."""
            data = request.get_json()
            if not data:
                return jsonify({
                    "success": False,
                    "error": "JSON payload required"
                }), 400

            required_fields = ["name", "email", "department", "role"]
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        "success": False,
                        "error": f"Missing required field: {field}"
                    }), 400

            try:
                ad = SimulatedAD()
                username = username_from_email(data["email"])

                # Check if user exists
                if ad.get_user(username):
                    return jsonify({
                        "success": False,
                        "error": "User already exists"
                    }), 409

                user = ADUser(
                    username=username,
                    name=data["name"],
                    email=data["email"],
                    department=data["department"],
                    role=data["role"],
                    ou=OU_BY_DEPARTMENT.get(data["department"], "OU=Users,DC=company,DC=com"),
                    groups=ROLE_ACCESS_MATRIX.get(data["department"], {}).get("groups", []),
                    permissions=ROLE_ACCESS_MATRIX.get(data["department"], {}).get("permissions", []),
                    status=data.get("status", "active"),
                    created_at=datetime.utcnow().isoformat(),
                )

                ad.create_user(user)
                log_event("api_create_user", username, f"via API")

                return jsonify({
                    "success": True,
                    "message": "User created successfully",
                    "user": asdict(user)
                }), 201

            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

        @app.route("/api/users/<username>", methods=["PUT"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_update_user(username: str):
            """Update an existing user."""
            data = request.get_json()
            if not data:
                return jsonify({
                    "success": False,
                    "error": "JSON payload required"
                }), 400

            try:
                ad = SimulatedAD()
                if not ad.get_user(username):
                    return jsonify({
                        "success": False,
                        "error": "User not found"
                    }), 404

                ad.update_user(username, data)
                log_event("api_update_user", username, f"via API: {list(data.keys())}")

                return jsonify({
                    "success": True,
                    "message": "User updated successfully"
                })

            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

        @app.route("/api/users/<username>", methods=["DELETE"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_delete_user(username: str):
            """Delete a user."""
            try:
                ad = SimulatedAD()
                if not ad.get_user(username):
                    return jsonify({
                        "success": False,
                        "error": "User not found"
                    }), 404

                ad.delete_user(username)
                log_event("api_delete_user", username, "via API")

                return jsonify({
                    "success": True,
                    "message": "User deleted successfully"
                })

            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

        @app.route("/api/users/bulk-update", methods=["POST"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_bulk_update_users():
            """Bulk update multiple users."""
            data = request.get_json()
            if not data or "updates" not in data:
                return jsonify({
                    "success": False,
                    "error": "JSON payload with 'updates' array required"
                }), 400

            updates = data["updates"]
            if not isinstance(updates, list):
                return jsonify({
                    "success": False,
                    "error": "'updates' must be an array"
                }), 400

            results = []
            success_count = 0
            error_count = 0

            ad = SimulatedAD()
            for update_item in updates:
                username = update_item.get("username")
                update_data = update_item.get("data", {})

                if not username:
                    results.append({"error": "Missing username"})
                    error_count += 1
                    continue

                try:
                    if not ad.get_user(username):
                        results.append({"username": username, "error": "User not found"})
                        error_count += 1
                        continue

                    ad.update_user(username, update_data)
                    log_event("api_bulk_update", username, f"via API: {list(update_data.keys())}")
                    results.append({"username": username, "status": "updated"})
                    success_count += 1

                except Exception as e:
                    results.append({"username": username, "error": str(e)})
                    error_count += 1

            return jsonify({
                "success": True,
                "summary": {
                    "total": len(updates),
                    "successful": success_count,
                    "failed": error_count
                },
                "results": results
            })

        @app.route("/api/users/bulk-deactivate", methods=["POST"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_bulk_deactivate_users():
            """Bulk deactivate multiple users."""
            data = request.get_json()
            if not data or "usernames" not in data:
                return jsonify({
                    "success": False,
                    "error": "JSON payload with 'usernames' array required"
                }), 400

            usernames = data["usernames"]
            if not isinstance(usernames, list):
                return jsonify({
                    "success": False,
                    "error": "'usernames' must be an array"
                }), 400

            results = []
            success_count = 0
            error_count = 0

            ad = SimulatedAD()
            for username in usernames:
                try:
                    if not ad.get_user(username):
                        results.append({"username": username, "error": "User not found"})
                        error_count += 1
                        continue

                    ad.deactivate_user(username)
                    log_event("api_bulk_deactivate", username, "via API")
                    results.append({"username": username, "status": "deactivated"})
                    success_count += 1

                except Exception as e:
                    results.append({"username": username, "error": str(e)})
                    error_count += 1

            return jsonify({
                "success": True,
                "summary": {
                    "total": len(usernames),
                    "successful": success_count,
                    "failed": error_count
                },
                "results": results
            })

        @app.route("/api/audit", methods=["GET"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_get_audit_log():
            """Get audit log entries with optional filtering."""
            limit = int(request.args.get("limit", 100))
            action_filter = request.args.get("action")
            username_filter = request.args.get("username")

            rows = fetch_recent_users(limit=limit)
            audit_entries = []

            for row in rows:
                entry = {
                    "event_time": row[0],
                    "action": row[1],
                    "username": row[2],
                    "details": row[3]
                }

                # Apply filters
                if action_filter and entry["action"] != action_filter:
                    continue
                if username_filter and entry["username"] != username_filter:
                    continue

                audit_entries.append(entry)

            return jsonify({
                "success": True,
                "count": len(audit_entries),
                "audit_log": audit_entries
            })

        @app.route("/api/reports/users", methods=["GET"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_reports_users():
            """Get user reports with filtering and aggregation."""
            status_filter = request.args.get("status")
            department_filter = request.args.get("department")
            date_from = request.args.get("from")
            date_to = request.args.get("to")

            ad = SimulatedAD()
            users = ad.list_users()

            # Apply filters
            if status_filter:
                users = [u for u in users if u.get("status") == status_filter]
            if department_filter:
                users = [u for u in users if u.get("department") == department_filter]

            # Date filtering (if created_at is available)
            if date_from or date_to:
                filtered_users = []
                for user in users:
                    created_at = user.get("created_at", "")
                    if created_at:
                        try:
                            user_date = parse_date(created_at).date()
                            if date_from:
                                from_date = parse_date(date_from).date()
                                if user_date < from_date:
                                    continue
                            if date_to:
                                to_date = parse_date(date_to).date()
                                if user_date > to_date:
                                    continue
                        except:
                            pass  # Skip date filtering if parsing fails
                    filtered_users.append(user)
                users = filtered_users

            # Generate summary statistics
            total_users = len(users)
            active_users = len([u for u in users if u.get("status") == "active"])
            inactive_users = len([u for u in users if u.get("status") == "inactive"])

            department_counts = {}
            for user in users:
                dept = user.get("department", "Unknown")
                department_counts[dept] = department_counts.get(dept, 0) + 1

            return jsonify({
                "success": True,
                "summary": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "inactive_users": inactive_users,
                    "departments": department_counts
                },
                "users": users
            })

        @app.route("/api/reports/export", methods=["GET"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_reports_export():
            """Export user data as CSV or Excel."""
            format_type = request.args.get("format", "csv").lower()
            status_filter = request.args.get("status")
            department_filter = request.args.get("department")

            if format_type not in ["csv", "excel"]:
                return jsonify({
                    "success": False,
                    "error": "Format must be 'csv' or 'excel'"
                }), 400

            ad = SimulatedAD()
            users = ad.list_users()

            # Apply filters
            if status_filter:
                users = [u for u in users if u.get("status") == status_filter]
            if department_filter:
                users = [u for u in users if u.get("department") == department_filter]

            # Convert to DataFrame
            df = pd.DataFrame(users)

            if format_type == "csv":
                csv_data = df.to_csv(index=False)
                response = app.response_class(
                    csv_data,
                    mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=users_export.csv"}
                )
                return response
            else:  # excel
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Users', index=False)
                output.seek(0)

                response = app.response_class(
                    output.getvalue(),
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={"Content-Disposition": "attachment;filename=users_export.xlsx"}
                )
                return response

        @app.route("/api/users/export", methods=["GET"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_users_export():
            """Export full user database."""
            format_type = request.args.get("format", "json").lower()

            ad = SimulatedAD()
            users = ad.list_users()

            if format_type == "json":
                return jsonify({
                    "success": True,
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "total_users": len(users),
                    "users": users
                })
            elif format_type == "csv":
                df = pd.DataFrame(users)
                csv_data = df.to_csv(index=False)
                response = app.response_class(
                    csv_data,
                    mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=users_full_export.csv"}
                )
                return response
            else:
                return jsonify({
                    "success": False,
                    "error": "Format must be 'json' or 'csv'"
                }), 400

        @app.route("/api/users/import", methods=["POST"])
        @api_key_required
        @rate_limit(max_requests=API_RATE_LIMIT_REQUESTS, window_seconds=API_RATE_LIMIT_WINDOW)
        def api_users_import():
            """Import users from JSON payload with conflict resolution."""
            data = request.get_json()
            if not data or "users" not in data:
                return jsonify({
                    "success": False,
                    "error": "JSON payload with 'users' array required"
                }), 400

            users_to_import = data["users"]
            conflict_resolution = data.get("conflict_resolution", "skip")  # skip, update, error

            if not isinstance(users_to_import, list):
                return jsonify({
                    "success": False,
                    "error": "'users' must be an array"
                }), 400

            if conflict_resolution not in ["skip", "update", "error"]:
                return jsonify({
                    "success": False,
                    "error": "conflict_resolution must be 'skip', 'update', or 'error'"
                }), 400

            results = []
            success_count = 0
            error_count = 0
            skipped_count = 0

            ad = SimulatedAD()
            for user_data in users_to_import:
                username = user_data.get("username") or username_from_email(user_data.get("email", ""))

                if not username:
                    results.append({"error": "Missing username or email"})
                    error_count += 1
                    continue

                # Check for existing user
                existing_user = ad.get_user(username)
                if existing_user:
                    if conflict_resolution == "skip":
                        results.append({"username": username, "status": "skipped", "reason": "User exists"})
                        skipped_count += 1
                        continue
                    elif conflict_resolution == "error":
                        results.append({"username": username, "error": "User already exists"})
                        error_count += 1
                        continue
                    # conflict_resolution == "update" - continue with update

                try:
                    if existing_user:
                        # Update existing user
                        ad.update_user(username, user_data)
                        log_event("api_import_update", username, "via API import")
                        results.append({"username": username, "status": "updated"})
                    else:
                        # Create new user - ensure required fields
                        required_fields = ["name", "email", "department", "role"]
                        missing_fields = [f for f in required_fields if f not in user_data]
                        if missing_fields:
                            results.append({"username": username, "error": f"Missing fields: {missing_fields}"})
                            error_count += 1
                            continue

                        # Create ADUser object
                        user = ADUser(
                            username=username,
                            name=user_data["name"],
                            email=user_data["email"],
                            department=user_data["department"],
                            role=user_data["role"],
                            ou=OU_BY_DEPARTMENT.get(user_data["department"], "OU=Users,DC=company,DC=com"),
                            groups=ROLE_ACCESS_MATRIX.get(user_data["department"], {}).get("groups", []),
                            permissions=ROLE_ACCESS_MATRIX.get(user_data["department"], {}).get("permissions", []),
                            status=user_data.get("status", "active"),
                            created_at=user_data.get("created_at", datetime.utcnow().isoformat()),
                        )
                        ad.create_user(user)
                        log_event("api_import_create", username, "via API import")
                        results.append({"username": username, "status": "created"})

                    success_count += 1

                except Exception as e:
                    results.append({"username": username, "error": str(e)})
                    error_count += 1

            return jsonify({
                "success": True,
                "summary": {
                    "total": len(users_to_import),
                    "successful": success_count,
                    "skipped": skipped_count,
                    "failed": error_count
                },
                "results": results
            })

    return app


def _read_users_df() -> pd.DataFrame:
    if not USERS_JSON.exists():
        return pd.DataFrame(columns=["username", "name", "email", "department", "role", "status", "created_at"])
    try:
        data = json.loads(USERS_JSON.read_text(encoding="utf-8"))
        return pd.DataFrame(data.get("users", []))
    except Exception:
        return pd.DataFrame(columns=["username", "name", "email", "department", "role", "status", "created_at"])


# Create app instance for Gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


