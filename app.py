import os
import secrets
from datetime import datetime, timedelta

import requests
from flask import Flask, request, session, render_template
from flask_sqlalchemy import SQLAlchemy


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    secrets.token_hex(32)
)

database_url = os.environ.get(
    "DATABASE_URL",
    "sqlite:///super_admin.db"
)

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

SUPER_ADMIN_TOKEN = os.environ.get(
    "SUPER_ADMIN_TOKEN"
)

SUPER_ADMIN_ID = str(
    os.environ.get(
        "SUPER_ADMIN_ID",
        ""
    )
)

APP_URL = os.environ.get(
    "APP_URL",
    "https://telegram-super-admin2.onrender.com"
).rstrip("/")


# ============================================================
# DATABASE
# ============================================================

class ManagedBot(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    username = db.Column(
        db.String(150)
    )

    token = db.Column(
        db.Text,
        nullable=False,
        unique=True
    )

    status = db.Column(
        db.String(30),
        default="CONNECTED",
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class SetupSession(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    token = db.Column(
        db.String(200),
        unique=True,
        nullable=False
    )

    chat_id = db.Column(
        db.String(100),
        nullable=False
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=False
    )


with app.app_context():
    db.create_all()


# ============================================================
# TELEGRAM API
# ============================================================

def telegram(method, data=None):

    if not SUPER_ADMIN_TOKEN:
        return None

    url = (
        "https://api.telegram.org/"
        f"bot{SUPER_ADMIN_TOKEN}/{method}"
    )

    try:

        response = requests.post(
            url,
            json=data or {},
            timeout=20
        )

        return response.json()

    except requests.RequestException:
        return None


# ============================================================
# SEND MESSAGE
# ============================================================

def send_message(chat_id, text, keyboard=None):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    return telegram(
        "sendMessage",
        payload
    )


# ============================================================
# MAIN MENU
# ============================================================

def main_menu(chat_id):

    keyboard = {
        "inline_keyboard": [

            [
                {
                    "text": "🤖 Manage Bots",
                    "callback_data": "manage_bots"
                }
            ],

            [
                {
                    "text": "📊 Dashboard",
                    "callback_data": "dashboard"
                }
            ],

            [
                {
                    "text": "🔔 Notifications",
                    "callback_data": "notifications"
                }
            ],

            [
                {
                    "text": "⚙️ Settings",
                    "callback_data": "settings"
                }
            ]

        ]
    }

    send_message(
        chat_id,
        "👑 SUPER ADMIN\n\n"
        "Karibu kwenye mfumo mkuu wa "
        "kusimamia bots zako.\n\n"
        "Chagua huduma:",
        keyboard
    )


# ============================================================
# MANAGE BOTS
# ============================================================

def manage_bots(chat_id):

    bots = ManagedBot.query.order_by(
        ManagedBot.id.desc()
    ).all()

    if not bots:

        text = (
            "🤖 MANAGE BOTS\n\n"
            "Hakuna bot iliyounganishwa bado."
        )

    else:

        lines = [
            "🤖 MANAGE BOTS",
            "",
            "Bots zilizounganishwa:",
            ""
        ]

        for bot in bots:

            username = (
                f"@{bot.username}"
                if bot.username
                else "-"
            )

            lines.append(
                f"🆔 #{bot.id}\n"
                f"🤖 {bot.name}\n"
                f"👤 {username}\n"
                f"🟢 {bot.status}\n"
            )

        text = "\n".join(lines)

    keyboard = {
        "inline_keyboard": [

            [
                {
                    "text": "➕ Add Bot",
                    "callback_data": "add_bot"
                }
            ],

            [
                {
                    "text": "🔄 Refresh",
                    "callback_data": "manage_bots"
                }
            ],

            [
                {
                    "text": "⬅️ Main Menu",
                    "callback_data": "main_menu"
                }
            ]

        ]
    }

    send_message(
        chat_id,
        text,
        keyboard
    )


# ============================================================
# SECURE REGISTRATION SESSION
# ============================================================

def create_setup_session(chat_id):

    old_sessions = SetupSession.query.filter_by(
        chat_id=str(chat_id)
    ).all()

    for old in old_sessions:
        db.session.delete(old)

    setup_token = secrets.token_urlsafe(32)

    expires = datetime.utcnow() + timedelta(
        minutes=10
    )

    setup = SetupSession(
        token=setup_token,
        chat_id=str(chat_id),
        expires_at=expires
    )

    db.session.add(setup)
    db.session.commit
