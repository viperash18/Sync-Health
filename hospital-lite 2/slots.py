"""
slots.py — turning a doctor's working hours into bookable time slots, and
working out which of those slots are still free on a given day.

We store only work_start, work_end, and slot_minutes on each doctor, then
generate the individual slot times on the fly. That keeps the data small and
means changing a doctor's hours instantly changes their slots.
"""

from datetime import date, datetime, timedelta
from db import query


def today_str():
    """Local 'YYYY-MM-DD' for defaulting date pickers and 'today' queries."""
    return date.today().isoformat()


def generate_slots(doctor):
    """All slot times for a doctor as ['09:00', '09:30', ...]."""
    start = datetime.strptime(doctor["work_start"], "%H:%M")
    end = datetime.strptime(doctor["work_end"], "%H:%M")
    step = timedelta(minutes=doctor["slot_minutes"])
    slots, t = [], start
    while t < end:
        slots.append(t.strftime("%H:%M"))
        t += step
    return slots


def available_slots(doctor, appt_date):
    """Slots for that doctor/date with the already-taken ones removed."""
    taken_rows = query(
        """SELECT appt_time FROM appointments
            WHERE doctor_id = ? AND appt_date = ? AND status != 'cancelled'""",
        (doctor["id"], appt_date),
    )
    taken = {r["appt_time"] for r in taken_rows}
    return [s for s in generate_slots(doctor) if s not in taken]
