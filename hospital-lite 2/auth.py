"""
auth.py — login state and access control.

Login state lives in Flask's `session`, which is a cookie that is
cryptographically SIGNED with the app's SECRET_KEY (so a user cannot tamper with
their own role) and marked httponly (so page JavaScript cannot read it).

Passwords are never stored in plain text. We use Werkzeug's
generate_password_hash / check_password_hash (PBKDF2 by default) — the same
library Flask ships with, so no extra dependency.

The two decorators below are the access-control gate. Put @login_required or
@role_required("admin") above a route and the gate runs before the view does.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, g, abort
from werkzeug.security import generate_password_hash, check_password_hash

from db import query


def hash_password(raw):
    return generate_password_hash(raw)


def verify_password(raw, hashed):
    return check_password_hash(hashed, raw)


def login_user(user_row):
    """Store the minimum needed to identify the user on later requests."""
    session.clear()
    session["user_id"] = user_row["id"]
    session["role"] = user_row["role"]
    session["name"] = user_row["name"]


def logout_user():
    session.clear()


def current_user():
    """Load the full user row for the logged-in user, or None. Cached on g."""
    if "user" not in g:
        uid = session.get("user_id")
        g.user = query("SELECT * FROM users WHERE id = ?", (uid,), one=True) if uid else None
    return g.user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please log in first.", "warn")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    """Allow only the listed roles. Use as @role_required('staff', 'admin')."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return redirect(url_for("auth.login"))
            if user["role"] not in roles:
                abort(403)  # logged in, but not allowed here
            return view(*args, **kwargs)
        return wrapped
    return decorator
