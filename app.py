import os
import secrets
from datetime import datetime, timedelta

import requests
from flask import (
    Flask,
    request,
    session,
    render_template,
    redirect,
    url_for
)
from flask_sqlalchemy import SQLAlchemy


# ============================================================
# APP
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
# ENVIRONMENT
# ============================================================

SUPER_ADMIN_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN"
)

ADMIN_CHAT_ID = str(
    os.environ.get(
        "ADMIN_CHAT_ID",
        ""
    )
)

APP_URL = os.environ.get(
    "APP_URL",
    "https://telegram-super-admin2.onrender.com"
).rstrip("/")


# ============================================================
# DATABASE MODELS
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
        nullable=False
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
# SEND TELEGRAM MESSAGE
# ============================================================

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
            "🤖 MANAGE BOTS\n",
            "Bots zilizounganishwa:\n"
        ]

        for bot in bots:

            username = (
                f"@{bot.username}"
                if bot.username
                else "Username haijapatikana"
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
# CREATE SECURE ADD-BOT SESSION
# ============================================================

def create_setup_session(chat_id):

    # Remove old sessions for this admin
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
    db.session.commit()

    return setup_token


# ============================================================
# START ADD BOT
# ============================================================

def start_add_bot(chat_id):

    setup_token = create_setup_session(
        chat_id
    )

    setup_url = (
        f"{APP_URL}/admin/add-bot"
        f"?key={setup_token}"
    )

    keyboard = {
        "inline_keyboard": [

            [
                {
                    "text": "🔐 Open Secure Registration",
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

        "➕ ADD NEW BOT\n\n"

        "Tutatumia ukurasa salama wa usajili "
        "badala ya kuweka BotFather token "
        "kwenye Telegram chat.\n\n"

        "🔐 Link hii ni ya muda mfupi na "
        "itaisha baada ya dakika 10.\n\n"

        "Hatua:\n"
        "1️⃣ Fungua registration page\n"
        "2️⃣ Weka jina la bot\n"
        "3️⃣ Weka BotFather token\n"
        "4️⃣ Mfumo utathibitisha token\n"
        "5️⃣ Bot itaongezwa kwenye Super Admin",

        keyboard
    )


# ============================================================
# VERIFY TELEGRAM BOT TOKEN
# ============================================================

def verify_bot_token(token):

    if not token:
        return None

    try:

        response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=15
        )

        return response.json()

    except requests.RequestException:
        return None


# ============================================================
# SECURE ADD BOT PAGE
# ============================================================

@app.get("/admin/add-bot")
def add_bot_page():

    key = request.args.get(
        "key",
        ""
    ).strip()

    if not key:

        return (
            "<h2>Link ya usajili haipo.</h2>"
            "<p>Rudi Telegram Super Admin "
            "na uchague Add Bot tena.</p>"
        ), 400

    setup = SetupSession.query.filter_by(
        token=key
    ).first()

    if not setup:

        return (
            "<h2>Link si sahihi.</h2>"
            "<p>Tafadhali tengeneza link mpya "
            "kupitia Super Admin.</p>"
        ), 403

    if datetime.utcnow() > setup.expires_at:

        db.session.delete(setup)
        db.session.commit()

        return (
            "<h2>Link imekwisha muda.</h2>"
            "<p>Rudi Telegram na utengeneze "
            "link mpya.</p>"
        ), 410

    # Save setup key in secure server session.
    session["bot_setup_key"] = key

    return render_template(
        "add_bot.html"
    )


# ============================================================
# REGISTER BOT
# ============================================================

@app.post("/admin/add-bot")
def register_bot():

    key = session.get(
        "bot_setup_key"
    )

    if not key:

        return (
            "<h2>Session imekwisha.</h2>"
            "<p>Rudi Telegram Super Admin "
            "na uchague Add Bot tena.</p>"
        ), 403

    setup = SetupSession.query.filter_by(
        token=key
    ).first()

    if not setup:

        session.pop(
            "bot_setup_key",
            None
        )

        return (
            "<h2>Registration session si sahihi.</h2>"
        ), 403

    if datetime.utcnow() > setup.expires_at:

        db.session.delete(setup)
        db.session.commit()

        session.pop(
            "bot_setup_key",
            None
        )

        return (
            "<h2>Registration session imekwisha.</h2>"
            "<p>Rudi Telegram na uchague Add Bot tena.</p>"
        ), 410

    name = request.form.get(
        "name",
        ""
    ).strip()

    token = request.form.get(
        "token",
        ""
    ).strip()

    username = request.form.get(
        "username",
        ""
    ).strip()

    if not name or not token:

        return (
            "<h2>Jaza sehemu zote muhimu.</h2>"
            "<p>Jina na BotFather token vinahitajika.</p>"
        ), 400

    # Verify token with Telegram
    result = verify_bot_token(
        token
    )

    if not result or not result.get("ok"):

        return (
            "<h2>❌ Bot token si sahihi.</h2>"
            "<p>Rudi nyuma na uweke "
            "BotFather token sahihi.</p>"
        ), 400

    bot_info = result.get(
        "result",
        {}
    )

    telegram_username = bot_info.get(
        "username"
    )

    # Use Telegram username if the form was blank
    if not username:

        username = (
            telegram_username or ""
        )

    # Check whether token already exists
    existing = ManagedBot.query.filter_by(
        token=token
    ).first()

    if existing:

        session.pop(
            "bot_setup_key",
            None
        )

        return (
            "<h2>⚠️ Bot tayari imeunganishwa.</h2>"
            f"<p>{existing.name}</p>"
            f"<p>@{existing.username or '-'}</p>"
            "<p>Rudi kwenye Super Admin.</p>"
        ), 409

    bot = ManagedBot(
        name=name,
        username=username,
        token=token,
        status="CONNECTED"
    )

    db.session.add(bot)

    # One-time setup session
    db.session.delete(setup)

    db.session.commit()

    session.pop(
        "bot_setup_key",
        None
    )

    # Send confirmation to Super Admin
    send_message(

        setup.chat_id,

        "✅ BOT CONNECTED!\n\n"

        f"🤖 Jina: {bot.name}\n"
        f"👤 Username: @{bot.username or '-'}\n"
        f"🆔 ID: #{bot.id}\n"
        f"🟢 Status: {bot.status}\n\n"

        "Bot imeongezwa kwenye Super Admin."
    )

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width,initial-scale=1">
        <title>Bot Connected</title>

        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #0f1720;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                padding: 20px;
            }

            .card {
                width: 100%;
                max-width: 500px;
                background: #192533;
                border-radius: 20px;
                padding: 30px;
                text-align: center;
                box-shadow: 0 10px 40px #0008;
            }

            .success {
                font-size: 60px;
            }

            h1 {
                color: #22c55e;
            }

            .bot {
                background: #101923;
                padding: 18px;
                border-radius: 12px;
                margin: 20px 0;
                text-align: left;
            }

            a {
                display: block;
                background: #1683ff;
                color: white;
                text-decoration: none;
                padding: 14px;
                border-radius: 10px;
                font-weight: bold;
            }
        </style>
    </head>

    <body>

        <div class="card">

            <div class="success">✅</div>

            <h1>Bot Connected!</h1>

            <p>
                Bot yako imeunganishwa
                kwa mafanikio.
            </p>

            <div class="bot">

                <strong>🤖 Bot Name</strong><br>
                """ + bot.name + """

                <br><br>

                <strong>👤 Username</strong><br>
                @""" + (bot.username or "-") + """

                <br><br>

                <strong>🟢 Status</strong><br>
                CONNECTED

            </div>

            <a href="/">
                Return to Super Admin
            </a>

        </div>

    </body>
    </html>
    """


# ============================================================
# TELEGRAM WEBHOOK
# ============================================================

@app.post("/telegram/webhook")
def telegram_webhook():

    update = request.get_json(
        silent=True
    ) or {}

    # --------------------------------------------------------
    # CALLBACK QUERY
    # --------------------------------------------------------

    callback = update.get(
        "callback_query"
    )

    if callback:

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

        chat_id = str(
            chat.get(
                "id",
                ""
            )
        )

        # Only configured admin
        if (
            ADMIN_CHAT_ID
            and chat_id != ADMIN_CHAT_ID
        ):

            telegram(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_id,
                    "text": "⛔ Huna ruhusa."
                }
            )

            return {
                "ok": True
            }

        if data == "manage_bots":

            manage_bots(
                chat_id
            )

        elif data == "add_bot":

            start_add_bot(
                chat_id
            )

        elif data == "main_menu":

            main_menu(
                chat_id
            )

        elif data == "dashboard":

            count = ManagedBot.query.count()

            send_message(

                chat_id,

                "📊 DASHBOARD\n\n"

                f"🤖 Connected Bots: {count}\n\n"

                "Super Admin iko active."
            )

        elif data == "notifications":

            send_message(

                chat_id,

                "🔔 NOTIFICATIONS\n\n"
                "Hakuna notification mpya."
            )

        elif data == "settings":

            send_message(

                chat_id,

                "⚙️ SETTINGS\n\n"

                "Super Admin settings\n\n"

                "🟢 System: Online\n"
                "🔐 Security: Active"
            )

        telegram(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_id
            }
        )

        return {
            "ok": True
        }

    # --------------------------------------------------------
    # NORMAL MESSAGE
    # --------------------------------------------------------

    message = update.get(
        "message"
    )

    if message:

        chat = message.get(
            "chat",
            {}
        )

        chat_id = str(
            chat.get(
                "id",
                ""
            )
        )

        text = message.get(
            "text",
            ""
        ).strip()

        if (
            ADMIN_CHAT_ID
            and chat_id != ADMIN_CHAT_ID
        ):

            send_message(
                chat_id,
                "⛔ Huna ruhusa ya kutumia "
                "Super Admin."
            )

            return {
                "ok": True
            }

        if text == "/start":

            main_menu(
                chat_id
            )

    return {
        "ok": True
    }


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width,initial-scale=1">

        <title>Super Admin</title>

        <style>

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #0f1720;
                color: white;
            }

            .container {
                max-width: 700px;
                margin: 60px auto;
                padding: 20px;
                text-align: center;
            }

            .card {
                background: #192533;
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0 10px 40px #0008;
            }

            h1 {
                margin-bottom: 10px;
            }

            .status {
                color: #22c55e;
                font-weight: bold;
            }

        </style>
    </head>

    <body>

        <div class="container">

            <div class="card">

                <h1>👑 MKOPO Super Admin</h1>

                <p class="status">
                    🟢 System Online
                </p>

                <p>
                    Telegram Super Admin
                    is running successfully.
                </p>

            </div>

        </div>

    </body>
    </html>
    """


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )
