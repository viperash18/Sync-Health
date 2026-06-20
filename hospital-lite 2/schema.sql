-- Hospital-Lite database schema (SQLite)
--
-- Design note: we separate clinical PATIENT records from login USERS.
--   * Staff (admin / reception / doctor) and self-service patients have a row
--     in `users` (they can log in).
--   * Every person who gets treated has a row in `patients` (their clinical
--     record). Reception can register a walk-in patient who has NO login.
--   * A patient who signs up online gets BOTH: a patients row and a users row
--     whose `patient_id` links the two.
-- Appointments reference the clinical `patient_id`, so the online-booking and
-- reception-booking paths unify on the same record.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS doctors (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    specialization TEXT    NOT NULL,
    room           TEXT    NOT NULL DEFAULT '',
    work_start     TEXT    NOT NULL DEFAULT '09:00',  -- 'HH:MM'
    work_end       TEXT    NOT NULL DEFAULT '17:00',  -- 'HH:MM'
    slot_minutes   INTEGER NOT NULL DEFAULT 30,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS patients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    phone      TEXT    NOT NULL UNIQUE,   -- we match/reuse patients by phone
    age        INTEGER,
    gender     TEXT    NOT NULL DEFAULT '' CHECK (gender IN ('male','female','other','')),
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('admin','reception','doctor','patient')),
    -- Set only for doctor logins: links the account to its Doctor profile.
    doctor_id     INTEGER REFERENCES doctors(id),
    -- Set only for patient logins: links the account to its clinical record.
    patient_id    INTEGER REFERENCES patients(id),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS appointments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    doctor_id  INTEGER NOT NULL REFERENCES doctors(id),
    appt_date  TEXT    NOT NULL,                 -- 'YYYY-MM-DD'
    appt_time  TEXT    NOT NULL,                 -- 'HH:MM'
    reason     TEXT    NOT NULL DEFAULT '',
    status     TEXT    NOT NULL DEFAULT 'booked'
               CHECK (status IN ('booked','checked-in','in-progress','completed','cancelled')),
    note       TEXT    NOT NULL DEFAULT '',      -- doctor's visit note
    created_by TEXT    NOT NULL DEFAULT 'patient' CHECK (created_by IN ('patient','reception')),
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- The double-booking guard. A PARTIAL UNIQUE INDEX: a given doctor can have only
-- one *active* appointment in a slot, but cancelled appointments are excluded,
-- so a freed-up slot can be rebooked. This makes the rule enforced by the
-- database itself, not just by an application check that could race.
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_slot
    ON appointments(doctor_id, appt_date, appt_time)
    WHERE status != 'cancelled';

CREATE INDEX IF NOT EXISTS idx_appt_doctor_date ON appointments(doctor_id, appt_date);
CREATE INDEX IF NOT EXISTS idx_appt_patient     ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appt_status      ON appointments(status);
