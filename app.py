import os
import secrets
from datetime import datetime

import requests
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS


# =========================================================
# APPLICATION
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    secrets.token_hex(32)
)

CORS(app)


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is missing")

# Render/PostgreSQL compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================================================
# DATABASE MODEL
# =========================================================

class Application(db.Model):

    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)

    country = db.Column(db.String(100))
    location = db.Column(db.String(150))
    occupation = db.Column(db.String(150))

    package = db.Column(db.String(100))
    amount = db.Column(db.String(100))

    status = db.Column(
        db.String(30),
        default="PENDING",
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    approved_at = db.Column(
        db.DateTime,
        nullable=True
    )

    rejected_at = db.Column(
        db.DateTime,
        nullable=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone": self.phone,
            "country": self.country,
            "location": self.location,
            "occupation": self.occupation,
            "package": self.package,
            "amount": self.amount,
            "status": self.status,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "approved_at": (
                self.approved_at.isoformat()
                if self.approved_at
                else None
            ),
            "rejected_at": (
                self.rejected_at.isoformat()
                if self.rejected_at
                else None
            )
        }


# =========================================================
# TELEGRAM CONFIGURATION
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


def telegram_url():
    if not BOT_TOKEN:
        return None

    return (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )


def send_telegram(message, buttons=None):
    """
    Send a message to Telegram.

    buttons can contain Telegram inline keyboard rows.
    """

    url = telegram_url()

    if not url or not CHAT_ID:
        print("Telegram is not configured.")
        return False

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": buttons
        }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        print(
            "Telegram response:",
            response.status_code,
            response.text
        )

        return response.ok

    except Exception as error:
        print("Telegram error:", error)
        return False


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

with app.app_context():
    db.create_all()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    try:
        return render_template("index.html")

    except Exception:
        return jsonify({
            "status": "online",
            "service": "Application API",
            "message": "Server is running"
        })


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    try:

        db.session.execute(
            db.text("SELECT 1")
        )

        return jsonify({
            "status": "healthy",
            "database": "connected",
            "service": "online"
        }), 200

    except Exception as error:

        return jsonify({
            "status": "unhealthy",
            "database": "error",
            "error": str(error)
        }), 500


# =========================================================
# APPLY
# =========================================================

@app.route("/apply", methods=["POST"])
def apply():

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "No application data received"
            }), 400

        full_name = str(
            data.get("full_name", "")
        ).strip()

        phone = str(
            data.get("phone", "")
        ).strip()

        country = str(
            data.get("country", "")
        ).strip()

        location = str(
            data.get("location", "")
        ).strip()

        occupation = str(
            data.get("occupation", "")
        ).strip()

        package = str(
            data.get("package", "")
        ).strip()

        amount = str(
            data.get("amount", "")
        ).strip()


        # -------------------------------------------------
        # REQUIRED FIELDS
        # -------------------------------------------------

        if not full_name:
            return jsonify({
                "success": False,
                "message": "Full name is required"
            }), 400

        if not phone:
            return jsonify({
                "success": False,
                "message": "Phone number is required"
            }), 400


        # -------------------------------------------------
        # SAVE APPLICATION
        # -------------------------------------------------

        application = Application(

            full_name=full_name,
            phone=phone,
            country=country,
            location=location,
            occupation=occupation,
            package=package,
            amount=amount,
            status="PENDING"
        )

        db.session.add(application)
        db.session.commit()


        # -------------------------------------------------
        # TELEGRAM MESSAGE
        # -------------------------------------------------

        message = f"""
<b>NEW APPLICATION</b>

<b>Application ID:</b> #{application.id}

<b>Name:</b> {full_name}

<b>Phone:</b> {phone}

<b>Country:</b> {country}

<b>Location:</b> {location}

<b>Occupation:</b> {occupation}

<b>Package:</b> {package}

<b>Amount:</b> {amount}

<b>Status:</b> PENDING

Please review the application.
"""

        buttons = [
            [
                {
                    "text": "✅ APPROVE",
                    "callback_data": f"approve_{application.id}"
                },
                {
                    "text": "❌ REJECT",
                    "callback_data": f"reject_{application.id}"
                }
            ]
        ]

        telegram_sent = send_telegram(
            message,
            buttons
        )


        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return jsonify({
            "success": True,
            "message": "Application submitted successfully",
            "application_id": application.id,
            "status": application.status,
            "telegram_notification": telegram_sent
        }), 201


    except Exception as error:

        db.session.rollback()

        print("APPLICATION ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Unable to submit application",
            "error": str(error)
        }), 500


# =========================================================
# GET APPLICATION
# =========================================================

@app.route("/application/<int:application_id>", methods=["GET"])
def get_application(application_id):

    application = db.session.get(
        Application,
        application_id
    )

    if not application:

        return jsonify({
            "success": False,
            "message": "Application not found"
        }), 404

    return jsonify({
        "success": True,
        "application": application.to_dict()
    })


# =========================================================
# APPLICATION STATUS
# =========================================================

@app.route("/application/<int:application_id>/status")
def application_status(application_id):

    application = db.session.get(
        Application,
        application_id
    )

    if not application:

        return jsonify({
            "success": False,
            "message": "Application not found"
        }), 404

    return jsonify({
        "success": True,
        "application_id": application.id,
        "status": application.status
    })


# =========================================================
# ADMIN APPLICATION LIST
# =========================================================

@app.route("/admin/applications")
def admin_applications():

    applications = Application.query.order_by(
        Application.id.desc()
    ).all()

    return jsonify({
        "success": True,
        "count": len(applications),
        "applications": [
            application.to_dict()
            for application in applications
        ]
    })


# =========================================================
# APPROVE APPLICATION
# =========================================================

@app.route(
    "/admin/application/<int:application_id>/approve",
    methods=["POST"]
)
def approve_application(application_id):

    application = db.session.get(
        Application,
        application_id
    )

    if not application:

        return jsonify({
            "success": False,
            "message": "Application not found"
        }), 404

    application.status = "APPROVED"
    application.approved_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Application approved",
        "application": application.to_dict()
    })


# =========================================================
# REJECT APPLICATION
# =========================================================

@app.route(
    "/admin/application/<int:application_id>/reject",
    methods=["POST"]
)
def reject_application(application_id):

    application = db.session.get(
        Application,
        application_id
    )

    if not application:

        return jsonify({
            "success": False,
            "message": "Application not found"
        }), 404

    application.status = "REJECTED"
    application.rejected_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Application rejected",
        "application": application.to_dict()
    })


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():

    try:

        update = request.get_json(
            silent=True
        )

        if not update:
            return jsonify({
                "ok": True
            })


        callback_query = update.get(
            "callback_query"
        )

        if not callback_query:
            return jsonify({
                "ok": True
            })


        callback_data = callback_query.get(
            "data",
            ""
        )

        callback_id = callback_query.get(
            "id"
        )


        # -------------------------------------------------
        # APPROVE
        # -------------------------------------------------

        if callback_data.startswith("approve_"):

            application_id = int(
                callback_data.split("_")[1]
            )

            application = db.session.get(
                Application,
                application_id
            )

            if application:

                application.status = "APPROVED"
                application.approved_at = datetime.utcnow()

                db.session.commit()

                send_telegram(
                    f"""
<b>APPLICATION APPROVED</b>

<b>Application:</b> #{application.id}

<b>Name:</b> {application.full_name}

<b>Phone:</b> {application.phone}

<b>Status:</b> APPROVED
"""
                )


        # -------------------------------------------------
        # REJECT
        # -------------------------------------------------

        elif callback_data.startswith("reject_"):

            application_id = int(
                callback_data.split("_")[1]
            )

            application = db.session.get(
                Application,
                application_id
            )

            if application:

                application.status = "REJECTED"
                application.rejected_at = datetime.utcnow()

                db.session.commit()

                send_telegram(
                    f"""
<b>APPLICATION REJECTED</b>

<b>Application:</b> #{application.id}

<b>Name:</b> {application.full_name}

<b>Phone:</b> {application.phone}

<b>Status:</b> REJECTED
"""
                )


        # -------------------------------------------------
        # ANSWER TELEGRAM CALLBACK
        # -------------------------------------------------

        if BOT_TOKEN and callback_id:

            answer_url = (
                f"https://api.telegram.org/bot"
                f"{BOT_TOKEN}/answerCallbackQuery"
            )

            requests.post(
                answer_url,
                json={
                    "callback_query_id": callback_id
                },
                timeout=10
            )


        return jsonify({
            "ok": True
        })


    except Exception as error:

        print(
            "TELEGRAM WEBHOOK ERROR:",
            error
        )

        return jsonify({
            "ok": False
        }), 500


# =========================================================
# 404 HANDLER
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "message": "Endpoint not found"
    }), 404


# =========================================================
# 500 HANDLER
# =========================================================

@app.errorhandler(500)
def server_error(error):

    return jsonify({
        "success": False,
        "message": "Internal server error"
    }), 500


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
