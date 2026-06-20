# Hospital-Lite

A full-stack clinic appointment and queue management system, built with Flask and HTMX.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![HTMX](https://img.shields.io/badge/HTMX-live%20UI-3D72D7)](https://htmx.org/)
[![SQLite](https://img.shields.io/badge/SQLite-DB-07405E?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

Patients book appointments online and track them live. Reception runs the front desk and handles walk-ins. Doctors work through a live queue and leave visit notes. Admins get a dashboard for managing staff and doctors. Each role only ever sees its own screens.

Built by a team of 3.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Data Model](#data-model)
- [Getting Started](#getting-started)
- [Demo Logins](#demo-logins)
- [Project Structure](#project-structure)
- [Routes](#routes)
- [Design Decisions](#design-decisions)
- [Interview Questions](#interview-questions)
- [Limitations](#limitations)
- [License](#license)

## Overview

Hospital-Lite is a role-based clinic management webapp for a small practice. There are four roles, each with its own dashboard, all backed by one shared database:

| Role | What they do |
|---|---|
| Patient | Register, book an appointment with any active doctor, watch their appointment status update live |
| Reception | Run the front desk — register walk-ins, book on a patient's behalf, check patients in, cancel appointments |
| Doctor | Work through today's queue, move appointments through checked-in → in-progress → completed, leave a visit note |
| Admin | Manage doctors and staff, view a basic analytics dashboard |

## Features

- Role-based access control, with each role locked to its own routes via reusable decorators
- Slot-based booking — a doctor's working hours generate the bookable time slots automatically, and only free ones are shown
- Live updates without websockets — HTMX polling refreshes the doctor queue, reception board, and patient tracker every few seconds
- Double-booking prevention enforced at the database level, not just in application code
- Walk-in support — reception can register and book a patient with no online account
- Visit notes — doctors leave a short note when completing a visit, which the patient can see afterward
- A small analytics dashboard with per-doctor appointment breakdowns
- Hashed passwords and signed, httponly session cookies for authentication

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + Flask | Small and synchronous, easy to read, no hidden magic |
| Database | SQLite (`sqlite3` from the standard library) | Zero setup, and every query is plain parameterized SQL |
| Frontend | Jinja2 templates + HTMX | The server renders HTML, and HTMX swaps in fragments for live updates — almost no hand-written JavaScript |
| Auth | Flask sessions + Werkzeug hashing | Standard and secure, with no extra dependencies |

The live parts of the app — the patient tracker, doctor queue, and reception board — are done with HTMX polling. The page just asks the server for a fresh HTML fragment every few seconds, instead of using websockets. It's a simpler design to reason about and explain, at the cost of true push-based updates.

## Architecture

```
Browser (Jinja + HTMX)
        |
        |  HTTP requests / HTMX fragment swaps
        v
Flask app.py
  - 5 blueprints (auth, patient, doctor, reception, admin)
        |
        |  parameterized SQL only, via db.py
        v
SQLite
  - 4 tables
  - 1 partial unique index for double-booking prevention
```

## Data Model

Four tables. The schema deliberately keeps clinical records separate from login accounts:

| Table | Purpose |
|---|---|
| `doctors` | Name, specialization, room, working hours, slot length, active flag |
| `patients` | The clinical record — name, phone, age, gender |
| `users` | Logins. Staff and self-service patients have a row here; a doctor login carries a `doctor_id`, a patient login carries a `patient_id` |
| `appointments` | Patient + doctor + date/time + status + visit note |

Reception can register a walk-in patient with no app account at all. A patient who signs up online gets both a `patients` row and a linked `users` row. Appointments always reference the clinical `patient_id`, so both booking paths end up pointing at the same underlying record.

The double-booking guard looks like this:

```sql
CREATE UNIQUE INDEX uq_active_slot
    ON appointments(doctor_id, appt_date, appt_time)
    WHERE status != 'cancelled';
```

A doctor can only have one active appointment in a given slot. Cancelling an appointment frees that slot back up. Because this lives in the database rather than in application logic, it can't be raced by two requests arriving at the same time.

## Getting Started

Requires Python 3.10 or later.

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
python seed.py     # creates the database and demo data
python app.py      # runs on http://127.0.0.1:5000
```

## Demo Logins

| Role | Email | Password |
|---|---|---|
| Admin | `admin@hospital.com` | `admin123` |
| Reception | `reception@hospital.com` | `reception123` |
| Doctor | `asha.mehta@hospital.com` | `doctor123` |
| Patient | `patient@hospital.com` | `patient123` |

The easiest way to see it work: open the patient login in one browser window and Dr. Mehta's doctor login in another. Book an appointment with her as the patient, check that patient in from reception, then advance the visit as the doctor. Each screen picks up the change on its own, no refresh needed.

## Project Structure

```
hospital-lite/
├── app.py               # App factory: config, blueprints, error pages
├── db.py                # The only file that talks to SQLite directly
├── auth.py              # Password hashing, login_required / role_required decorators
├── slots.py             # Turns a doctor's working hours into bookable slots
├── booking.py           # Shared booking logic (find-or-create patient, race-safe insert)
├── schema.sql           # Table definitions and the partial unique index
├── seed.py              # Rebuilds the database with demo data
├── routes_auth.py       # register / login / logout
├── routes_patient.py    # booking, slot picker, appointment tracking
├── routes_doctor.py     # live queue, status updates, visit notes
├── routes_reception.py  # front desk, walk-in registration, check-in
├── routes_admin.py      # analytics dashboard, doctor and staff management
├── templates/           # Jinja2 pages and HTMX partials
└── static/style.css
```

## Routes

| Blueprint | Route | Method | Purpose |
|---|---|---|---|
| Auth | `/register` | GET, POST | Patient self-registration |
| Auth | `/login`, `/logout` | GET, POST | Session authentication |
| Patient | `/book` | GET, POST | Book an appointment |
| Patient | `/book/slots` | GET | Live slot picker fragment |
| Patient | `/appointments` | GET | View own appointments |
| Patient | `/appointments/list` | GET | Live appointment status fragment |
| Doctor | `/doctor` | GET | Today's queue |
| Doctor | `/doctor/board` | GET | Live queue fragment |
| Doctor | `/doctor/advance/<id>` | POST | Move appointment to next status |
| Doctor | `/doctor/cancel/<id>` | POST | Cancel an appointment |
| Reception | `/reception` | GET | Front desk view |
| Reception | `/reception/board` | GET | Live board fragment |
| Reception | `/reception/book` | POST | Register and book a walk-in |
| Reception | `/reception/checkin/<id>` | POST | Check a patient in |
| Reception | `/reception/cancel/<id>` | POST | Cancel an appointment |
| Admin | `/admin` | GET | Analytics dashboard |
| Admin | `/admin/doctors` | GET, POST | Manage doctors |
| Admin | `/admin/doctors/<id>/toggle` | POST | Activate or deactivate a doctor |
| Admin | `/admin/staff` | GET, POST | Manage staff accounts |

## Design Decisions

A few things worth calling out about how this was built, beyond what's typical for a project this size:

**Double-booking is prevented at the database layer.** A partial unique index guarantees a doctor can only have one active appointment per slot, while cancelled appointments free that slot back up. An application-only check (look up the slot, then insert if free) leaves a race window between the check and the insert. The database closes that window.

**Availability is computed, not stored.** A doctor's slots come from their working hours and slot length, generated on the fly by `slots.py`. Change a doctor's hours and their availability updates immediately, with nothing to migrate or recompute.

**Visit notes carry over to the patient's view.** When a doctor completes a visit, the note they leave shows up on the patient's own appointment history.

**Patients and users are deliberately separate tables.** This is what lets reception register someone who's never going to create an account, while still letting self-service patients log in and track things themselves.

## Interview Questions

A few questions this project tends to come up in, and how to answer them.

**How do you stop two people from booking the same slot?**
Two layers. The booking page only ever shows slots that are currently free, and the real guard is a partial unique index in the database — `UNIQUE(doctor_id, appt_date, appt_time) WHERE status != 'cancelled'`. If two requests do race each other, the database rejects the second insert and the user sees "that slot was just taken." The reason it's enforced at the database level rather than purely in application code is that an application-only check has a window between checking availability and writing the row.

**How does the live queue work without websockets?**
HTMX polling. The relevant element on the page re-fetches a small HTML fragment every few seconds using `hx-trigger="every 3s"`. It's simple to reason about and debug. If this needed to scale to push-based updates instead of polling, the natural next step would be Server-Sent Events or websockets.

**Why are patients and users separate tables?**
A patient is a clinical record. A user is a login. Reception needs to be able to register a walk-in who never creates an account, and a person shouldn't need a login just to be treated. Patients who sign up online end up with both records, linked through `patient_id`.

**How is SQL injection prevented?**
Every value coming from a user is passed in as a `?` parameter (see `db.py`) rather than being formatted directly into the query string, so the driver handles escaping.

**How does role-based access work?**
A user's id and role are stored in Flask's signed, httponly session cookie at login. Routes are protected with `login_required` and `role_required("doctor")` style decorators defined in `auth.py`. Doctors are further restricted to acting only on their own appointments, which is checked inside each handler rather than relying on the decorator alone.

**Where do a doctor's time slots come from?**
Only `work_start`, `work_end`, and `slot_minutes` are stored. `slots.py` generates the actual list of times on demand, so editing a doctor's hours changes their availability immediately.

**How would this scale, and what are its limitations?**
SQLite is single-writer, which is fine for one clinic but wouldn't hold up under heavy concurrent load. The SQL itself is standard, so moving to PostgreSQL would be a fairly small migration. Polling would need to become SSE or websockets at higher scale. Beyond that, this version is missing automated tests, audit logging, and more thorough input validation.

## Limitations

- SQLite was chosen for simplicity. The schema is standard SQL and would port to PostgreSQL without much rework.
- Real-time updates rely on polling rather than websockets — a deliberate trade-off for simplicity over a course/portfolio scope.
- This is a course/portfolio project. It runs on Flask's dev server, with no rate limiting or email verification.

## License

This project was built for educational and portfolio purposes. Add a license of your choice — MIT is a reasonable default — if you plan to make the repository public.
