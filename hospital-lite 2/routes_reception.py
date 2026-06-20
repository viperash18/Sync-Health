"""
routes_reception.py — the front desk.

Reception sees the whole schedule for a chosen day, registers walk-in patients
and books on their behalf (by phone, reusing existing records), and checks
patients in / cancels. The day's board polls itself for live updates.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query, execute
from auth import role_required
from slots import available_slots, today_str
from booking import find_or_create_patient, create_appointment

bp = Blueprint("reception", __name__)


def schedule_for(day):
    return query(
        """SELECT a.*, p.name AS patient_name, p.phone,
                  d.name AS doctor_name, d.specialization
             FROM appointments a
             JOIN patients p ON p.id = a.patient_id
             JOIN doctors  d ON d.id = a.doctor_id
            WHERE a.appt_date = ? AND a.status != 'cancelled'
            ORDER BY a.appt_time""",
        (day,),
    )


@bp.route("/reception")
@role_required("reception", "admin")
def desk():
    day = request.args.get("day") or today_str()
    doctors = query("SELECT * FROM doctors WHERE active = 1 ORDER BY name")
    return render_template("reception_desk.html", day=day, doctors=doctors, today=today_str())


@bp.route("/reception/board")
@role_required("reception", "admin")
def board_fragment():
    day = request.args.get("day") or today_str()
    return render_template("partials/reception_board.html", appointments=schedule_for(day), day=day)


@bp.route("/reception/slots")
@role_required("reception", "admin")
def slots_fragment():
    doctor_id = request.args.get("doctor_id")
    appt_date = request.args.get("appt_date") or today_str()
    doctor = query("SELECT * FROM doctors WHERE id = ?", (doctor_id,), one=True) if doctor_id else None
    free = available_slots(doctor, appt_date) if doctor else []
    return render_template("partials/slot_buttons.html", slots=free, appt_date=appt_date)


@bp.route("/reception/book", methods=["POST"])
@role_required("reception", "admin")
def book():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    age = request.form.get("age") or None
    gender = request.form.get("gender", "")
    doctor_id = request.form.get("doctor_id")
    appt_date = request.form.get("appt_date")
    appt_time = request.form.get("appt_time")
    reason = request.form.get("reason", "").strip()

    if not (name and phone and doctor_id and appt_date and appt_time):
        flash("Name, phone, doctor, date, and time are required.", "error")
        return redirect(url_for("reception.desk", day=appt_date or today_str()))

    patient_id = find_or_create_patient(name, phone, age, gender)
    ok, msg = create_appointment(patient_id, doctor_id, appt_date, appt_time, reason, "reception")
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("reception.desk", day=appt_date))


@bp.route("/reception/checkin/<int:appt_id>", methods=["POST"])
@role_required("reception", "admin")
def checkin(appt_id):
    execute(
        "UPDATE appointments SET status = 'checked-in' WHERE id = ? AND status = 'booked'",
        (appt_id,),
    )
    return board_fragment()


@bp.route("/reception/cancel/<int:appt_id>", methods=["POST"])
@role_required("reception", "admin")
def cancel(appt_id):
    execute(
        "UPDATE appointments SET status = 'cancelled' WHERE id = ? AND status NOT IN ('completed')",
        (appt_id,),
    )
    return board_fragment()
