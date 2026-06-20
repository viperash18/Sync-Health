"""
app.py — the application factory for Hospital-Lite.

Builds the Flask app, registers the five blueprints (auth, patient, doctor,
reception, admin), wires up the per-request database teardown, and exposes the
current user to every template.

Run it:
    python seed.py        # one-time: create tables + demo data
    python app.py         # start the dev server on http://127.0.0.1:5000
"""

import os
from flask import Flask, render_template

from db import close_db
from auth import current_user

import routes_auth
import routes_patient
import routes_doctor
import routes_reception
import routes_admin


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["DATABASE"] = os.environ.get("DATABASE", "hospital.db")

    app.teardown_appcontext(close_db)

    @app.context_processor
    def inject_user():
        return {"user": current_user()}

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                               message="You don't have access to that page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="Page not found."), 404

    app.register_blueprint(routes_auth.bp)
    app.register_blueprint(routes_patient.bp)
    app.register_blueprint(routes_doctor.bp)
    app.register_blueprint(routes_reception.bp)
    app.register_blueprint(routes_admin.bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
