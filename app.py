import os
import secrets
from datetime import datetime, timedelta

import requests
from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    secrets.token_hex(32)
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///super_admin.db"
)

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
# ENVIRONMENT VARIABLES
# =========================================================

SUPER_ADMIN_TOKEN = os.environ.get(
    "SUPER_ADMIN_TOKEN",
    ""
).strip()

SUPER_ADMIN_ID = str(
    os.environ.get(
        "SUPER_ADMIN_ID",
        ""
    )
).strip()

APP_URL = os.environ.get(
    "APP_URL",
    "https://telegram-super-admin2.onrender.com"
).rstrip("/")


# =========================================================
# DATABASE MODELS
# =========================================================

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
        db.String(150),
        nullable=True
    )

    token = db.Column(
        db.Text,
        nullable=False,
        unique=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="CONNECTED"
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
        db.String(255),
        nullable=False,
        unique=True
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


# =========================================================
# TELEGRAM API
# =========================================================

def telegram(method, data=None):

    if not SUPER_ADMIN_TOKEN:
        print("ERROR: SUPER_ADMIN_TOKEN is missing")
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

        print(
            f"Telegram {method}: "
            f"{response.status_code}"
        )

        return response.json()

    except requests.RequestException as error:

        print(
            f"Telegram error: {error}"
        )

        return None


# =========================================================
# SEND MESSAGE
# =========================================================

def send_message(
    chat_id,
    text,
    keyboard=None
):

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


# =========================================================
# ANSWER CALLBACK
# =========================================================

def answer_callback(
    callback_id,
    text=""
):

    return telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id,
            "text": text
        }
    )


# =========================================================
# SUPER ADMIN CHECK
# =========================================================

def is_super_admin(chat_id):

    if not SUPER_ADMIN_ID:
        return False

    return str(chat_id) == str(
        SUPER_ADMIN_ID
    )


# =========================================================
# MAIN MENU
# =========================================================

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


# =========================================================
# MANAGE BOTS
# =========================================================

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


# =========================================================
# CREATE SECURE SETUP SESSION
# =========================================================

def create_setup_session(chat_id):

    old_sessions = SetupSession.query.filter_by(
        chat_id=str(chat_id)
    ).all()

    for old in old_sessions:

        db.session.delete(old)

    setup_token = secrets.token_urlsafe(32)

    expires = (
        datetime.utcnow()
        + timedelta(minutes=10)
    )

    setup = SetupSession(
        token=setup_token,
        chat_id=str(chat_id),
        expires_at=expires
    )

    db.session.add(setup)

    db.session.commit()

    return setup_token


# =========================================================
# ADD BOT
# =========================================================

def add_bot(chat_id):

    setup_token = create_setup_session(
        chat_id
    )

    setup_url = (
        f"{APP_URL}/setup/"
        f"{setup_token}"
    )

    keyboard = {
        "inline_keyboard": [

            [
                {
                    "text": "🔐 Open Secure Bot Setup",
                    "url": setup_url
                }
            ],

            [
                {
                    "text": "⬅️ Manage Bots",
                    "callback_data": "manage_bots"
                }
            ]

        ]
    }

    send_message(

        chat_id,

        "➕ ADD BOT\n\n"

        "Hatua inayofuata tutaunganisha "
        "bot mpya kupitia ukurasa salama.\n\n"

        "🔐 Usitume Bot Token kwenye Telegram chat.\n\n"

        "⏱️ Link hii ni halali kwa dakika 10 tu.\n\n"

        "Bonyeza kitufe hapa chini:",

        keyboard
    )


# =========================================================
# VERIFY TELEGRAM BOT TOKEN
# =========================================================

def verify_bot_token(token):

    try:

        response = requests.get(

            f"https://api.telegram.org/"
            f"bot{token}/getMe",

            timeout=15
        )

        data = response.json()

        if not data.get("ok"):

            return None

        return data.get("result")

    except requests.RequestException:

        return None

    except ValueError:

        return None


# =========================================================
# SECURE BOT SETUP PAGE
# =========================================================

@app.route(
    "/setup/<setup_token>",
    methods=["GET", "POST"]
)
def setup_bot(setup_token):

    setup = SetupSession.query.filter_by(
        token=setup_token
    ).first()

    if not setup:

        return (
            "❌ Link hii si sahihi "
            "au imekwisha.",
            404
        )

    if setup.expires_at < datetime.utcnow():

        db.session.delete(setup)
        db.session.commit()

        return (
            "⏰ Link hii imekwisha muda wake."
            "<br><br>"
            "Rudi Telegram na utengeneze "
            "link mpya.",
            410
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        token = request.form.get(
            "token",
            ""
        ).strip()

        if not name:

            return render_template(
                "setup.html",
                error="Tafadhali weka jina la bot."
            )

        if not token:

            return render_template(
                "setup.html",
                error="Tafadhali weka Bot Token."
            )

        bot_info = verify_bot_token(
            token
        )

        if not bot_info:

            return render_template(
                "setup.html",
                error=(
                    "❌ Bot Token si sahihi "
                    "au Telegram haikupokea."
                )
            )

        username = bot_info.get(
            "username",
            ""
        )

        existing = ManagedBot.query.filter_by(
            token=token
        ).first()

        if existing:

            return render_template(
                "setup.html",
                error=(
                    "⚠️ Bot hii tayari "
                    "imeunganishwa."
                )
            )

        bot = ManagedBot(

            name=name,

            username=username,

            token=token,

            status="CONNECTED"
        )

        db.session.add(bot)

        db.session.delete(setup)

        db.session.commit()

        username_text = (
            f"@{username}"
            if username
            else "-"
        )

        send_message(

            setup.chat_id,

            "✅ BOT CONNECTED\n\n"

            f"🤖 Jina: {name}\n"

            f"👤 Username: "
            f"{username_text}\n"

            f"🆔 Bot ID: #{bot.id}\n\n"

            "🟢 Bot imeunganishwa "
            "kwenye Super Admin."
        )

        return render_template(
            "connected.html",
            bot=bot
        )

    return render_template(
        "setup.html"
    )


# =========================================================
# DASHBOARD
# =========================================================

def dashboard(chat_id):

    total = ManagedBot.query.count()

    connected = ManagedBot.query.filter_by(
        status="CONNECTED"
    ).count()

    disconnected = ManagedBot.query.filter_by(
        status="DISCONNECTED"
    ).count()

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
                    "text": "⬅️ Main Menu",
                    "callback_data": "main_menu"
                }
            ]

        ]
    }

    send_message(

        chat_id,

        "📊 DASHBOARD\n\n"

        f"🤖 Total Bots: {total}\n"

        f"🟢 Connected: {connected}\n"

        f"🔴 Disconnected: {disconnected}\n\n"

        "Mfumo wa Super Admin uko tayari.",

        keyboard
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

def notifications(chat_id):

    keyboard = {
        "inline_keyboard": [

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

        "🔔 NOTIFICATIONS\n\n"

        "Hakuna notification mpya kwa sasa.",

        keyboard
    )


# =========================================================
# SETTINGS
# =========================================================

def settings(chat_id):

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
                    "text": "⬅️ Main Menu",
                    "callback_data": "main_menu"
                }
            ]

        ]
    }

    send_message(

        chat_id,

        "⚙️ SETTINGS\n\n"

        "👑 Super Admin ID:\n"
        f"{SUPER_ADMIN_ID or '-'}\n\n"

        "🌐 Application URL:\n"
        f"{APP_URL}\n\n"

        "🔐 Token configuration: ACTIVE",

        keyboard
    )


# =========================================================
# TELEGRAM UPDATE HANDLER
# =========================================================

def process_update(update):

    # -----------------------------------------------------
    # NORMAL MESSAGE
    # -----------------------------------------------------

    message = update.get(
        "message"
    )

    if message:

        chat = message.get(
            "chat",
            {}
        )

        chat_id = chat.get(
            "id"
        )

        if not chat_id:
            return

        if not is_super_admin(
            chat_id
        ):

            send_message(
                chat_id,
                "⛔ Huna ruhusa ya kutumia bot hii."
            )

            return

        text = message.get(
            "text",
            ""
        ).strip()

        if text.startswith(
            "/start"
        ):

            main_menu(
                chat_id
            )

            return

        if text.startswith(
            "/menu"
        ):

            main_menu(
                chat_id
            )

            return

        if text.startswith(
            "/bots"
        ):

            manage_bots(
                chat_id
            )

            return

        if text.startswith(
            "/health"
        ):

            send_message(
                chat_id,
                "🟢 Super Admin Bot iko hai."
            )

            return

        main_menu(
            chat_id
        )

        return

    # -----------------------------------------------------
    # CALLBACK QUERY
    # -----------------------------------------------------

    callback = update.get(
        "callback_query"
    )

    if not callback:
        return

    callback_id = callback.get(
        "id"
    )

    data = callback.get(
        "data",
        ""
    )

    message = callback.get(
        "message",
        {}
    )

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get(
        "id"
    )

    if not chat_id:
        return

    if not is_super_admin(
        chat_id
    ):

        answer_callback(
            callback_id,
            "⛔ Huna ruhusa."
        )

        return

    answer_callback(
        callback_id
    )

    # -----------------------------------------------------
    # CALLBACK ACTIONS
    # -----------------------------------------------------

    if data == "main_menu":

        main_menu(
            chat_id
        )

    elif data == "manage_bots":

        manage_bots(
            chat_id
        )

    elif data == "add_bot":

        add_bot(
            chat_id
        )

    elif data == "dashboard":

        dashboard(
            chat_id
        )

    elif data == "notifications":

        notifications(
            chat_id
        )

    elif data == "settings":

        settings(
            chat_id
        )


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.route(
    "/telegram/webhook",
    methods=["POST"]
)
def telegram_webhook():

    update = request.get_json(
        silent=True
    )

    if not update:

        return {
            "ok": False,
            "error": "Invalid update"
        }, 400

    try:

        process_update(
            update
        )

    except Exception as error:

        print(
            "Webhook processing error:",
            error
        )

    return {
        "ok": True
    }


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return """
    <!DOCTYPE html>

    <html lang="en">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width,initial-scale=1.0">

        <title>MKOPO Super Admin</title>

        <style>

            body {
                margin:0;
                padding:30px;
                background:#101820;
                color:white;
                font-family:Arial,sans-serif;
                text-align:center;
            }

            .card {
                max-width:600px;
                margin:60px auto;
                background:#1d2935;
                padding:35px;
                border-radius:20px;
            }

            h1 {
                margin-bottom:10px;
            }

            .ok {
                color:#35d07f;
                font-weight:bold;
            }

        </style>

    </head>

    <body>

        <div class="card">

            <h1>👑 MKOPO Super Admin</h1>

            <p class="ok">
                🟢 System is running
            </p>

            <p>
                Telegram Super Admin system
                is online.
            </p>

            <p>
                Webhook:
                <strong>/telegram/webhook</strong>
            </p>

        </div>

    </body>

    </html>
    """


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return {
        "status": "ok",
        "service": "telegram-super-admin",
        "webhook": "/telegram/webhook"
    }


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return {
        "error": "Not Found",
        "status": 404
    }, 404


@app.errorhandler(500)
def server_error(error):

    return {
        "error": "Internal Server Error",
        "status": 500
    }, 500


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
