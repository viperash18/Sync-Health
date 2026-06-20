"""
routes_admin.py — admin area: an analytics dashboard, doctor management
(add / edit hours / toggle active), and staff account creation.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db import query, execute
from auth import role_required, hash_password
from slots import today_str

bp = Blueprint("admin", __name__)


@bp.route("/admin")
@role_required("admin")
def dashboard():
    today = today_str()
    stats = {
        "appts_today": query(
            "SELECT COUNT(*) AS n FROM appointments WHERE appt_date = ? AND status != 'cancelled'",
            (today,), one=True,
        )["n"],
        "completed_today": query(
            "SELECT COUNT(*) AS n FROM appointments WHERE appt_date = ? AND status = 'completed'",
            (today,), one=True,
        )["n"],
        "active_doctors": query(
            "SELECT COUNT(*) AS n FROM doctors WHERE active = 1", one=True
        )["n"],
        "total_patients": query("SELECT COUNT(*) AS n FROM patients", one=True)["n"],
    }
    # Appointments per doctor today (a simple GROUP BY aggregate).
    by_doctor = query(
        """SELECT d.name, d.specialization,
                  COUNT(a.id) AS booked,
                  SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) AS completed
             FROM doctors d
             LEFT JOIN appointments a
                    ON a.doctor_id = d.id AND a.appt_date = ? AND a.status != 'cancelled'
            WHERE d.active = 1
            GROUP BY d.id
            ORDER BY booked DESC, d.name""",
        (today,),
    )
    return render_template("admin/dashboard.html", stats=stats, by_doctor=by_doctor, today=today)


# --- doctors -------------------------------------------------------------------

@bp.route("/admin/doctors", methods=["GET", "POST"])
@role_required("admin")
def doctors():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        spec = request.form.get("specialization", "").strip()
        room = request.form.get("room", "").strip()
        work_start = request.form.get("work_start", "09:00")
        work_end = request.form.get("work_end", "17:00")
        slot_minutes = request.form.get("slot_minutes", "30")
        if not (name and spec):
            flash("Doctor name and specialization are required.", "error")
            return redirect(url_for("admin.doctors"))
        try:
            slot_minutes = int(slot_minutes)
            if slot_minutes <= 0:
                raise ValueError
        except ValueError:
            flash("Slot length must be a positive number of minutes.", "error")
            return redirect(url_for("admin.doctors"))

        execute(
            """INSERT INTO doctors (name, specialization, room, work_start, work_end, slot_minutes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, spec, room, work_start, work_end, slot_minutes),
        )
        flash(f"Added {name}.", "ok")
        return redirect(url_for("admin.doctors"))

    rows = query("SELECT * FROM doctors ORDER BY active DESC, name")
    return render_template("admin/doctors.html", doctors=rows)


@bp.route("/admin/doctors/<int:doctor_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_doctor(doctor_id):
    doc = query("SELECT * FROM doctors WHERE id = ?", (doctor_id,), one=True)
    if doc is None:
        abort(404)
    execute(
        "UPDATE doctors SET active = ? WHERE id = ?",
        (0 if doc["active"] else 1, doctor_id),
    )
    return redirect(url_for("admin.doctors"))


# --- staff accounts ------------------------------------------------------------

@bp.route("/admin/staff", methods=["GET", "POST"])
@role_required("admin")
def staff():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        doctor_id = request.form.get("doctor_id") or None

        if role not in ("admin", "reception", "doctor"):
            flash("Pick a valid staff role.", "error")
            return redirect(url_for("admin.staff"))
        if not (name and email) or len(password) < 6:
            flash("Name, email, and a 6+ character password are required.", "error")
            return redirect(url_for("admin.staff"))
        if query("SELECT 1 FROM users WHERE email = ?", (email,), one=True):
            flash("That email is already in use.", "error")
            return redirect(url_for("admin.staff"))
        if role == "doctor" and not doctor_id:
            flash("A doctor account must be linked to a doctor profile.", "error")
            return redirect(url_for("admin.staff"))

        execute(
            """INSERT INTO users (name, email, password_hash, role, doctor_id)
               VALUES (?, ?, ?, ?, ?)""",
            (name, email, hash_password(password), role, doctor_id if role == "doctor" else None),
        )
        flash(f"Created {role} account for {name}.", "ok")
        return redirect(url_for("admin.staff"))

    users = query(
        """SELECT u.*, d.name AS doctor_name
             FROM users u LEFT JOIN doctors d ON d.id = u.doctor_id
            WHERE u.role != 'patient'
            ORDER BY u.role, u.name"""
    )
    free_doctors = query(
        """SELECT * FROM doctors
            WHERE id NOT IN (SELECT doctor_id FROM users WHERE doctor_id IS NOT NULL)
            ORDER BY name"""
    )
    return render_template("admin/staff.html", users=users, free_doctors=free_doctors)
