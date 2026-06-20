"""
booking.py — shared booking logic used by BOTH the patient self-booking flow
and the reception desk. Keeping it here (instead of duplicating in two route
files) means the conflict-handling and patient-matching rules live in one place.
"""

import sqlite3
from db import get_db, query, execute


def find_or_create_patient(name, phone, age=None, gender=""):
    """Reuse an existing patient (matched by phone) or create a new record."""
    existing = query("SELECT * FROM patients WHERE phone = ?", (phone,), one=True)
    if existing:
        return existing["id"]
    return execute(
        "INSERT INTO patients (name, phone, age, gender) VALUES (?, ?, ?, ?)",
        (name, phone, age, gender or ""),
    )


def create_appointment(patient_id, doctor_id, appt_date, appt_time, reason, created_by):
    """
    Try to book a slot. Returns (ok, message).

    We rely on the partial UNIQUE index in the schema as the final authority:
    if two requests race for the same slot, the database rejects the second one
    with an IntegrityError and we turn that into a friendly message. This is
    safer than only checking availability in Python, which has a race window
    between the check and the insert.
    """
    db = get_db()
    try:
        db.execute(
            """INSERT INTO appointments
                   (patient_id, doctor_id, appt_date, appt_time, reason, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (patient_id, doctor_id, appt_date, appt_time, reason, created_by),
        )
        db.commit()
        return True, "Appointment booked."
    except sqlite3.IntegrityError:
        db.rollback()
        return False, "That slot was just taken. Please pick another time."
