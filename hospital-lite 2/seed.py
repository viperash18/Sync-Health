"""
seed.py — set up the database with demo data so you can log in immediately.

Run once:  python seed.py   (re-running wipes and rebuilds for a clean demo)

Demo logins:
    Admin      admin@hospital.com       / admin123
    Reception  reception@hospital.com   / reception123
    Doctor     asha.mehta@hospital.com  / doctor123   (also rohan.iyer, leena.kapoor)
    Patient    patient@hospital.com     / patient123
"""

import os
from app import app
from db import init_db, execute, query
from auth import hash_password
from slots import today_str, generate_slots


DOCTORS = [
    # name, specialization, room, start, end, slot_minutes
    ("Dr. Asha Mehta",   "Cardiology",  "201", "09:00", "13:00", 30),
    ("Dr. Rohan Iyer",   "Pediatrics",  "112", "10:00", "16:00", 20),
    ("Dr. Leena Kapoor", "Dermatology", "305", "09:00", "12:00", 30),
]


def seed():
    with app.app_context():
        db_path = app.config["DATABASE"]
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Removed old {db_path}")

        init_db()
        print("Created tables from schema.sql")

        # Admin + reception logins.
        execute("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                ("Hospital Admin", "admin@hospital.com", hash_password("admin123")))
        execute("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'reception')",
                ("Front Desk", "reception@hospital.com", hash_password("reception123")))

        # Doctors + their linked logins.
        doctor_ids = {}
        for name, spec, room, start, end, mins in DOCTORS:
            did = execute(
                """INSERT INTO doctors (name, specialization, room, work_start, work_end, slot_minutes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, spec, room, start, end, mins),
            )
            doctor_ids[name] = did
            email = name.lower().replace("dr. ", "").replace(" ", ".") + "@hospital.com"
            execute(
                "INSERT INTO users (name, email, password_hash, role, doctor_id) VALUES (?, ?, ?, 'doctor', ?)",
                (name, email, hash_password("doctor123"), did),
            )
            print(f"  Doctor login -> {email} / doctor123")

        # A demo patient with a login.
        pid = execute(
            "INSERT INTO patients (name, phone, age, gender) VALUES (?, ?, ?, ?)",
            ("Sample Patient", "9990001111", 34, "female"),
        )
        execute(
            "INSERT INTO users (name, email, password_hash, role, patient_id) VALUES (?, ?, ?, 'patient', ?)",
            ("Sample Patient", "patient@hospital.com", hash_password("patient123"), pid),
        )

        # A couple more walk-in patient records (no logins).
        pid2 = execute("INSERT INTO patients (name, phone, age, gender) VALUES (?, ?, ?, ?)",
                       ("Ramesh Gupta", "9990002222", 51, "male"))
        pid3 = execute("INSERT INTO patients (name, phone, age, gender) VALUES (?, ?, ?, ?)",
                       ("Meera Nair", "9990003333", 8, "female"))

        # Sample appointments for TODAY so the queues aren't empty.
        today = today_str()
        asha = doctor_ids["Dr. Asha Mehta"]
        rohan = doctor_ids["Dr. Rohan Iyer"]
        asha_slots = generate_slots(query("SELECT * FROM doctors WHERE id = ?", (asha,), one=True))
        rohan_slots = generate_slots(query("SELECT * FROM doctors WHERE id = ?", (rohan,), one=True))

        execute("""INSERT INTO appointments (patient_id, doctor_id, appt_date, appt_time, reason, status, created_by)
                   VALUES (?, ?, ?, ?, ?, 'booked', 'patient')""",
                (pid, asha, today, asha_slots[0], "Routine heart check-up"))
        execute("""INSERT INTO appointments (patient_id, doctor_id, appt_date, appt_time, reason, status, created_by)
                   VALUES (?, ?, ?, ?, ?, 'checked-in', 'reception')""",
                (pid2, asha, today, asha_slots[1], "Chest pain follow-up"))
        execute("""INSERT INTO appointments (patient_id, doctor_id, appt_date, appt_time, reason, status, created_by)
                   VALUES (?, ?, ?, ?, ?, 'booked', 'reception')""",
                (pid3, rohan, today, rohan_slots[0], "Fever and cough"))
        print("Created sample appointments for today")

        print("\nSeed complete. Demo logins:")
        print("  Admin      admin@hospital.com       / admin123")
        print("  Reception  reception@hospital.com   / reception123")
        print("  Doctor     asha.mehta@hospital.com  / doctor123")
        print("  Patient    patient@hospital.com     / patient123")


if __name__ == "__main__":
    seed()
