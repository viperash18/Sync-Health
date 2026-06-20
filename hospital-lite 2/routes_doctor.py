"""
routes_doctor.py — the doctor's live queue for today.

A doctor sees only their own appointments. They move each patient along:
booked -> checked-in -> in-progress -> completed, and record a short visit note
when finishing. The board polls itself so newly checked-in patients appear.
"""

from flask import Blueprint, render_template, request, abort
from db import query, execute
from auth import role_required, current_user
from slots import today_str

bp = Blueprint("doctor", __name__)

NEXT_STATUS = {
    "booked": "checked-in",
    "checked-in": "in-progress",
    "in-progress": "completed",
}


def my_today(doctor_id):
    return query(
        """SELECT a.*, p.name AS patient_name, p.age, p.gender, p.phone
             FROM appointments a JOIN patients p ON p.id = a.patient_id
            WHERE a.doctor_id = ? AND a.appt_date = ?
              AND a.status != 'cancelled'
            ORDER BY a.appt_time""",
        (doctor_id, today_str()),
    )


@bp.route("/doctor")
@role_required("doctor")
def queue():
    return render_template("doctor_queue.html", today=today_str())


@bp.route("/doctor/board")
@role_required("doctor")
def board_fragment():
    user = current_user()
    appts = my_today(user["doctor_id"]) if user["doctor_id"] else []
    return render_template("partials/doctor_board.html", appointments=appts)


def _owned(appt_id, doctor_id):
    """Fetch an appointment only if it belongs to this doctor."""
    return query(
        "SELECT * FROM appointments WHERE id = ? AND doctor_id = ?",
        (appt_id, doctor_id), one=True,
    )


@bp.route("/doctor/advance/<int:appt_id>", methods=["POST"])
@role_required("doctor")
def advance(appt_id):
    user = current_user()
    appt = _owned(appt_id, user["doctor_id"])
    if appt is None:
        abort(404)
    nxt = NEXT_STATUS.get(appt["status"])
    if nxt:
        note = request.form.get("note", "").strip()
        # When completing, also save the visit note if one was typed.
        if nxt == "completed" and note:
            execute(
                "UPDATE appointments SET status = ?, note = ? WHERE id = ?",
                (nxt, note, appt_id),
            )
        else:
            execute("UPDATE appointments SET status = ? WHERE id = ?", (nxt, appt_id))
    return board_fragment()


@bp.route("/doctor/cancel/<int:appt_id>", methods=["POST"])
@role_required("doctor")
def cancel(appt_id):
    user = current_user()
    appt = _owned(appt_id, user["doctor_id"])
    if appt is None:
        abort(404)
    execute(
        "UPDATE appointments SET status = 'cancelled' WHERE id = ? AND status != 'completed'",
        (appt_id,),
    )
    return board_fragment()
