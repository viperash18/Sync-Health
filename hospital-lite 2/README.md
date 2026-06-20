<div align="center">

# 🏥 Hospital-Lite

### A full-stack clinic appointment & queue management system

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![HTMX](https://img.shields.io/badge/HTMX-live%20UI-3D72D7)](https://htmx.org/)
[![SQLite](https://img.shields.io/badge/SQLite-DB-07405E?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#-license)

Patients book online and track their visit live. Reception runs the front desk.
Doctors work a live queue. Admins watch it all from a dashboard.
**Built by a team of 3.**

</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack--why-we-chose-it)
- [Architecture](#-architecture)
- [Data Model](#-data-model)
- [Getting Started](#-getting-started)
- [Demo Logins](#-demo-logins)
- [Project Structure](#-project-structure)
- [Routes / API Surface](#-routes--api-surface)
- [What Makes This Different](#-what-makes-this-different)
- [Interview Q&A](#-likely-interview-questions)
- [Scope & Limitations](#-honest-scope-notes)
- [License](#-license)

---

## 🩺 Overview

**Hospital-Lite** is a role-based clinic management webapp for a small practice. Four
roles, four purpose-built dashboards, one shared database:

| Role | Can do |
|---|---|
| 🧑‍⚕️ **Patient** | Register, book an appointment with any active doctor, watch their appointment status update live |
| 💁 **Reception** | Run the front desk: register walk-ins, book on their behalf, check patients in, cancel appointments |
| 🩺 **Doctor** | Work a live queue of today's appointments, advance status (checked-in → in-progress → completed), leave a visit note |
| 🛠️ **Admin** | Manage doctors and staff, view a per-doctor analytics dashboard |

---

## ✨ Features

- 🔐 **Role-based access control** — four roles, each locked to their own screens via reusable decorators
- 📅 **Slot-based booking** — a doctor's working hours auto-generate bookable time slots; only free ones are shown
- ⚡ **Live updates without websockets** — HTMX polling refreshes the doctor queue, reception board, and patient tracker every few seconds
- 🛑 **Database-enforced double-booking prevention** — a partial unique index closes the check-then-insert race condition that an app-only check would miss
- 🚶 **Walk-in support** — reception can register and book a patient who has no online account
- 📝 **Visit notes** — doctors leave a note on completion, visible to the patient afterward
- 📊 **Analytics dashboard** — per-doctor appointment breakdown for admins
- 🔒 **Secure auth** — hashed passwords (Werkzeug/PBKDF2) + signed, httponly session cookies

---

## 🧱 Tech Stack — and why we chose it

| Layer | Choice | Why |
|---|---|---|
| **Backend** | Python + Flask | Small, synchronous, easy to read — no hidden magic |
| **Database** | SQLite (`sqlite3` stdlib) | Zero setup; plain **parameterized SQL** — every query is visible and injection-safe |
| **Frontend** | Jinja2 templates + HTMX | Server renders HTML; HTMX swaps in fragments for live updates. Almost no hand-written JavaScript |
| **Auth** | Flask sessions + Werkzeug hashing | Standard, secure, zero extra dependencies |

The "live" behaviour (patient tracker, doctor queue, reception board) is done with
**HTMX polling** — the page asks the server for a fresh HTML fragment every few seconds —
instead of websockets, keeping the backend simple to explain and reason about.

---

## 🏗️ Architecture

```
┌─────────────┐      HTTP / HTMX fragments      ┌──────────────────┐
│   Browser   │ ◄──────────────────────────────► │   Flask app.py   │
│ (Jinja+HTMX)│                                   │  5 Blueprints    │
└─────────────┘                                   └────────┬─────────┘
                                                            │ parameterized SQL
                                                            ▼
                                                   ┌──────────────────┐
                                                   │   SQLite (db.py) │
                                                   │  4 tables + a    │
                                                   │ partial unique   │
                                                   │     index        │
                                                   └──────────────────┘
```

---

## 🗄️ Data Model

4 tables, deliberately separating **clinical records** from **login accounts**:

| Table | Purpose |
|---|---|
| `doctors` | name, specialization, room, working hours, slot length, active flag |
| `patients` | the *clinical* record — name, phone, age, gender |
| `users` | *logins*. Staff and self-service patients have a row here; a doctor login carries a `doctor_id`, a patient login carries a `patient_id` |
| `appointments` | patient + doctor + date/time + status + visit note |

> Reception can register a walk-in patient with **no app account**, while online patients
> get both a `patients` row and a linked `users` row. Appointments always reference the
> clinical `patient_id`, so both booking paths unify on the same record.

The double-booking guard:

```sql
CREATE UNIQUE INDEX uq_active_slot
    ON appointments(doctor_id, appt_date, appt_time)
    WHERE status != 'cancelled';
```

A doctor can have only one *active* appointment per slot; cancelling frees the slot
back up. This is enforced by the **database**, not just application logic — so it
can't be raced.

---

## 🚀 Getting Started

**Requirements:** Python 3.10+

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
python seed.py     # create the database + demo data
python app.py      # http://127.0.0.1:5000
```

---

## 🔑 Demo Logins

| Role | Email | Password |
|---|---|---|
| Admin | `admin@hospital.com` | `admin123` |
| Reception | `reception@hospital.com` | `reception123` |
| Doctor | `asha.mehta@hospital.com` | `doctor123` |
| Patient | `patient@hospital.com` | `patient123` |

**Best demo flow:** open **patient** in one window and **doctor (asha.mehta)** in another.
Book with Dr. Mehta as the patient → check the patient in from **reception** → advance the
visit as the doctor. Every screen updates on its own.

---

## 📁 Project Structure

```
hospital-lite/
├── app.py               # App factory: config, registers blueprints, error pages
├── db.py                # The ONLY file that talks to SQLite (parameterized queries)
├── auth.py              # Password hashing + @login_required / @role_required gates
├── slots.py             # Turns a doctor's hours into bookable slots + availability
├── booking.py           # Shared booking logic (find-or-create patient, race-safe insert)
├── schema.sql           # CREATE TABLE statements (4 tables + a partial unique index)
├── seed.py              # Wipes + rebuilds the DB with demo data
├── routes_auth.py       # register / login / logout
├── routes_patient.py    # patient: book, live slot picker, live appointment tracking
├── routes_doctor.py     # doctor: live queue, advance status, save visit note
├── routes_reception.py  # reception: front desk, register+book walk-ins, check-in
├── routes_admin.py      # admin: analytics dashboard, manage doctors, manage staff
├── templates/           # Jinja2 pages + HTMX partials/
└── static/style.css
```

---

## 🔌 Routes / API Surface

| Blueprint | Route | Method | Purpose |
|---|---|---|---|
| Auth | `/register` | GET/POST | Patient self-registration |
| | `/login` / `/logout` | GET/POST | Session auth |
| Patient | `/book` | GET/POST | Book an appointment |
| | `/book/slots` | GET | Live slot picker fragment |
| | `/appointments` | GET | View own appointments |
| | `/appointments/list` | GET | Live appointment-status fragment |
| Doctor | `/doctor` | GET | Today's queue |
| | `/doctor/board` | GET | Live queue fragment |
| | `/doctor/advance/<id>` | POST | Advance appointment status |
| | `/doctor/cancel/<id>` | POST | Cancel appointment |
| Reception | `/reception` | GET | Front desk view |
| | `/reception/board` | GET | Live board fragment |
| | `/reception/book` | POST | Register + book a walk-in |
| | `/reception/checkin/<id>` | POST | Check a patient in |
| | `/reception/cancel/<id>` | POST | Cancel appointment |
| Admin | `/admin` | GET | Analytics dashboard |
| | `/admin/doctors` | GET/POST | Manage doctors |
| | `/admin/doctors/<id>/toggle` | POST | Activate/deactivate doctor |
| | `/admin/staff` | GET/POST | Manage staff accounts |

---

## 🆚 What Makes This Different

1. **Database-enforced double-booking prevention** via a partial unique index — closes
   a real check-then-insert race that application-only checks leave open.
2. **Slot-based availability** generated live from a doctor's working hours.
3. **Visit notes** doctors leave on completion, visible to the patient.
4. **Analytics dashboard** with per-doctor `GROUP BY` breakdowns.
5. **No secrets in code or logs**; role-based access enforced via reusable decorators.

---

## 💬 Likely Interview Questions

<details>
<summary><b>How do you stop two people booking the same slot?</b></summary><br>

Two layers. The booking page only offers free slots, and the final guard is a
**partial unique index** in the database: `UNIQUE(doctor_id, appt_date, appt_time)
WHERE status != 'cancelled'`. If two requests race, the database rejects the second
insert and we show "that slot was just taken." We rely on the DB because an
application-only check has a race window between checking and inserting.
</details>

<details>
<summary><b>How is the live queue implemented without websockets?</b></summary><br>

HTMX polling: the board element re-fetches a small HTML fragment every few seconds
(`hx-trigger="every 3s"`). Simple and reliable. To push instead of poll at scale we'd
move to Server-Sent Events or websockets.
</details>

<details>
<summary><b>Why separate <code>patients</code> from <code>users</code>?</b></summary><br>

A patient is a clinical record; a user is a login. Reception must be able to register
a walk-in who never makes an account, and one person shouldn't need a login to be
treated. Online patients get both records, linked by `patient_id`.
</details>

<details>
<summary><b>How do you prevent SQL injection?</b></summary><br>

Every user value is passed as a `?` parameter (see `db.py`), never formatted into the
SQL string, so the driver escapes it.
</details>

<details>
<summary><b>How does role-based access work?</b></summary><br>

Login stores the user's id and role in Flask's signed, httponly session cookie. Routes
are guarded by `@login_required` and `@role_required("doctor")` decorators in `auth.py`;
doctors can additionally only act on their *own* appointments (checked in each handler).
</details>

<details>
<summary><b>Where do a doctor's time slots come from?</b></summary><br>

We store only `work_start`, `work_end`, and `slot_minutes`. `slots.py` generates the
individual times on the fly, so editing a doctor's hours instantly changes their
availability.
</details>

<details>
<summary><b>How would you scale this / what are the limitations?</b></summary><br>

SQLite is single-writer — fine for one clinic, not high concurrency; the SQL is standard
so PostgreSQL is a small migration. Polling would become SSE/websockets. We'd add
automated tests, audit logging, and stricter validation.
</details>

---

## 📋 Honest Scope Notes

- SQLite chosen for simplicity; schema is standard SQL and ports to PostgreSQL.
- Real-time updates use polling, not websockets (a deliberate simplicity choice).
- Course/portfolio project: dev server only, no rate limiting or email verification.

---

## 🎯 Résumé Bullets

> **Hospital-Lite — Clinic Appointment & Management System** *(Team of 3)*
> - Built a full-stack clinic platform with **role-based access** (patient / reception / doctor / admin) covering online booking, walk-in registration, a live doctor queue, visit notes, and an analytics dashboard.
> - Designed a relational schema separating clinical patient records from login accounts, and prevented appointment double-booking at the database layer using a **partial unique index** to eliminate check-then-insert race conditions.
> - Implemented live availability and real-time queue/status updates with **HTMX**, delivering an interactive multi-role UX with minimal client-side JavaScript.
> - Secured authentication with hashed passwords (PBKDF2) and signed-cookie sessions enforced via reusable route-level authorization decorators.

---

## 📄 License

This project is for educational/portfolio purposes. Add a license of your choice (MIT recommended) if you plan to publish it publicly.

---

<div align="center">

Made with ❤️ using Flask + HTMX — no framework magic, just clean code.

</div>
