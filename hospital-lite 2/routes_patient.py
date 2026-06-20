"""
routes_patient.py — what a logged-in patient does:
book an appointment, watch its status live, and see past visits.

The slot picker uses HTMX: choosing a doctor/date fetches the free slots for
that combination without a full page reload. The appointment list polls itself
so a patient sees 'checked-in' -> 'in-progress' -> 'completed' update live.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query
from auth import login_required, role_required, current_user
from slots import available_slots, today_str
from booking import create_appointment

bp = Blueprint("patient", __name__)


def _doctor(doctor_id):
    return query("SELECT * FROM doctors WHERE id = ? AND active = 1", (doctor_id,), one=True)


@bp.route("/book", methods=["GET", "POST"])
@role_required("patient")
def book():
    user = current_user()
    doctors = query("SELECT * FROM doctors WHERE active = 1 ORDER BY name")

    if request.method == "POST":
        doctor_id = request.form.get("doctor_id")
        appt_date = request.form.get("appt_date")
        appt_time = request.form.get("appt_time")
        reason = request.form.get("reason", "").strip()

        if not (doctor_id and appt_date and appt_time):
            flash("Please choose a doctor, date, and time.", "error")
            return redirect(url_for("patient.book"))

        doctor = _doctor(doctor_id)
        if doctor is None:
            flash("That doctor is not available.", "error")
            return redirect(url_for("patient.book"))

        ok, msg = create_appointment(
            user["patient_id"], doctor_id, appt_date, appt_time, reason, "patient"
        )
        flash(msg, "ok" if ok else "error")
        return redirect(url_for("patient.appointments") if ok else url_for("patient.book"))

    return render_template("patient_book.html", doctors=doctors, today=today_str())


@bp.route("/book/slots")
@role_required("patient", "reception")
def slots_fragment():
    """HTMX endpoint: returns clickable free-slot buttons for a doctor/date."""
    doctor_id = request.args.get("doctor_id")
    appt_date = request.args.get("appt_date") or today_str()
    doctor = query("SELECT * FROM doctors WHERE id = ?", (doctor_id,), one=True) if doctor_id else None
    free = available_slots(doctor, appt_date) if doctor else []
    return render_template("partials/slot_buttons.html", slots=free, appt_date=appt_date)


@bp.route("/appointments")
@role_required("patient")
def appointments():
    return render_template("patient_appointments.html")


@bp.route("/appointments/list")
@role_required("patient")
def appointments_fragment():
    """Polled by HTMX to keep the patient's status badges fresh."""
    user = current_user()
    rows = query(
        """SELECT a.*, d.name AS doctor_name, d.specialization, d.room
             FROM appointments a JOIN doctors d ON d.id = a.doctor_id
            WHERE a.patient_id = ?
            ORDER BY (a.status IN ('completed','cancelled')) ASC,
                     a.appt_date, a.appt_time""",
        (user["patient_id"],),
    )
    return render_template("partials/patient_appt_list.html", appointments=rows)
