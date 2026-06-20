"""routes_auth.py — register (patients only), login, logout."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query, execute
from auth import hash_password, verify_password, login_user, logout_user, current_user

bp = Blueprint("auth", __name__)


def home_for(role):
    """Each role's landing page after login."""
    return {
        "admin": "admin.dashboard",
        "reception": "reception.desk",
        "doctor": "doctor.queue",
        "patient": "patient.appointments",
    }[role]


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Public sign-up creates a patient account (clinical record + login)."""
    if current_user():
        return redirect(url_for(home_for(current_user()["role"])))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not (name and email and phone) or len(password) < 6:
            flash("Name, email, phone, and a 6+ character password are required.", "error")
            return render_template("register.html")
        if query("SELECT 1 FROM users WHERE email = ?", (email,), one=True):
            flash("That email is already registered.", "error")
            return render_template("register.html")

        # Reuse a clinical record if this phone already exists (e.g. a walk-in
        # who now wants an online account); otherwise create one.
        patient = query("SELECT * FROM patients WHERE phone = ?", (phone,), one=True)
        patient_id = patient["id"] if patient else execute(
            "INSERT INTO patients (name, phone) VALUES (?, ?)", (name, phone)
        )
        execute(
            """INSERT INTO users (name, email, password_hash, role, patient_id)
               VALUES (?, ?, ?, 'patient', ?)""",
            (name, email, hash_password(password), patient_id),
        )
        flash("Account created — please log in.", "ok")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for(home_for(current_user()["role"])))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user is None or not verify_password(password, user["password_hash"]):
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        login_user(user)
        flash(f"Welcome, {user['name']}.", "ok")
        return redirect(url_for(home_for(user["role"])))

    return render_template("login.html")


@bp.route("/logout")
def logout():
    logout_user()
    flash("Logged out.", "ok")
    return redirect(url_for("auth.login"))


@bp.route("/")
def index():
    user = current_user()
    if user:
        return redirect(url_for(home_for(user["role"])))
    return redirect(url_for("auth.login"))
