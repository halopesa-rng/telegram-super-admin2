import os
import secrets
import requests

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy


# =========================================================
# APP CONFIGURATION
# =========================================================

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


# =========================================================
# DATABASE
# =========================================================

class ManagedBot(db.Model):
    id = db.Column(db.Integer, primary_key=True)

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


class AdminState(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    chat_id = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    state = db.Column(
        db.String(50)
    )

    bot_name = db.Column(
        db.String(150)
    )


with app.app_context():
    db.create_all()


# =========================================================
# ENVIRONMENT
# =========================================================

SUPER_ADMIN_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN"
)

ADMIN_CHAT_ID = str(
    os.environ.get(
        "ADMIN_CHAT_ID",
        ""
    )
)


# =========================================================
# TELEGRAM API
# =========================================================

def telegram(method, data=None):

    if not SUPER_ADMIN_TOKEN:
        return None

    url = (
        f"https://api.telegram.org/"
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


# =========================================================
# SEND MESSAGE
# =========================================================

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
        "Chagua huduma kutoka kwenye menu.",
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
            "🤖 CONNECTED BOTS\n\n"
            "Hakuna bot iliyounganishwa bado."
        )

    else:

        lines = [
            "🤖 CONNECTED BOTS\n"
        ]

        for bot in bots:

            lines.append(
                f"🆔 #{bot.id}\n"
                f"🤖 {bot.name}\n"
                f"👤 @{bot.username or '-'}\n"
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
# ADD BOT - STEP 1
# =========================================================

def start_add_bot(chat_id):

    state = AdminState.query.filter_by(
        chat_id=str(chat_id)
    ).first()

    if not state:

        state = AdminState(
            chat_id=str(chat_id)
        )

        db.session.add(state)

    state.state = "WAITING_BOT_NAME"
    state.bot_name = None

    db.session.commit()

    send_message(
        chat_id,

        "➕ ADD NEW BOT\n\n"
        "Hatua ya 1/2\n\n"
        "Tuma jina la bot unayotaka kuunganisha.\n\n"
        "Mfano:\n"
        "HaloPesa MKOPO"
    )


# =========================================================
# ADD BOT - STEP 2
# =========================================================

def ask_for_token(chat_id, bot_name):

    state = AdminState.query.filter_by(
        chat_id=str(chat_id)
    ).first()

    if not state:
        return

    state.state = "WAITING_BOT_TOKEN"
    state.bot_name = bot_name

    db.session.commit()

    send_message(
        chat_id,

        "➕ ADD NEW BOT\n\n"
        "Hatua ya 2/2\n\n"
        f"Jina: {bot_name}\n\n"
        "Sasa tuma BotFather token ya bot hiyo.\n\n"
        "⚠️ Usitume token ya Super Admin.\n"
        "Tuma token ya bot unayotaka kuunganisha."
    )


# =========================================================
# VERIFY BOT TOKEN
# =========================================================

def check_bot_token(token):

    try:

        response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=15
        )

        return response.json()

    except requests.RequestException:

        return None


# =========================================================
# SAVE BOT
# =========================================================

def save_managed_bot(chat_id, token):

    state = AdminState.query.filter_by(
        chat_id=str(chat_id)
    ).first()

    if not state:
        return

    result = check_bot_token(token)

    if not result or not result.get("ok"):

        send_message(
            chat_id,

            "❌ TOKEN SI SAHIHI\n\n"
            "BotFather token haikuthibitishwa.\n\n"
            "Tafadhali tuma token sahihi tena."
        )

        return

    bot_info = result.get(
        "result",
        {}
    )

    username = bot_info.get(
        "username"
    )

    existing = ManagedBot.query.filter_by(
        token=token
    ).first()

    if existing:

        send_message(
            chat_id,

            "⚠️ BOT HII IMESHAUNGANISHWA.\n\n"
            f"🤖 {existing.name}\n"
            f"👤 @{existing.username or '-'}"
        )

        state.state = None
        state.bot_name = None

        db.session.commit()

        return

    bot = ManagedBot(
        name=state.bot_name,
        username=username,
        token=token,
        status="CONNECTED"
    )

    db.session.add(bot)

    state.state = None
    state.bot_name = None

    db.session.commit()

    send_message(
        chat_id,

        "✅ BOT CONNECTED\n\n"
        f"🤖 Jina: {bot.name}\n"
        f"👤 Username: @{bot.username or '-'}\n"
        "🟢 Status: CONNECTED\n\n"
        "Bot imehifadhiwa kwenye Super Admin."
    )

    manage_bots(chat_id)


# =========================================================
# START COMMAND
# =========================================================

def handle_start(chat_id):

    main_menu(chat_id)


# =========================================================
# TEXT MESSAGE HANDLER
# =========================================================

def handle_text(chat_id, text):

    state = AdminState.query.filter_by(
        chat_id=str(chat_id)
    ).first()

    if state and state.state == "WAITING_BOT_NAME":

        bot_name = text.strip()

        if len(bot_name) < 2:

            send_message(
                chat_id,
                "❌ Jina ni fupi sana. "
                "Tafadhali tuma jina la bot."
            )

            return

        ask_for_token(
            chat_id,
            bot_name
        )

        return

    if state and state.state == "WAITING_BOT_TOKEN":

        token = text.strip()

        if len(token) < 20:

            send_message(
                chat_id,
                "❌ Token haionekani kuwa sahihi."
            )

            return

        save_managed_bot(
            chat_id,
            token
        )

        return


# =========================================================
# CALLBACK HANDLER
# =========================================================

def handle_callback(callback):

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

    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:

        telegram(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_id,
                "text": "Huna ruhusa."
            }
        )

        return

    if data == "manage_bots":

        manage_bots(chat_id)

    elif data == "add_bot":

        start_add_bot(chat_id)

    elif data == "main_menu":

        main_menu(chat_id)

    elif data == "dashboard":

        send_message(
            chat_id,

            "📊 DASHBOARD\n\n"
            f"🤖 Connected bots: "
            f"{ManagedBot.query.count()}"
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
            "Super Admin settings."
        )

    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.post("/telegram/webhook")
def telegram_webhook():

    update = request.get_json(
        silent=True
    ) or {}

    callback = update.get(
        "callback_query"
    )

    if callback:

        handle_callback(
            callback
        )

        return {
            "ok": True
        }

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

        if not chat_id:
            return {
                "ok": True
            }

        # Only allow configured admin
        if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:

            send_message(
                chat_id,
                "⛔ Huna ruhusa ya kutumia Super Admin."
            )

            return {
                "ok": True
            }

        if text.lower() == "/start":

            handle_start(
                chat_id
            )

        else:

            handle_text(
                chat_id,
                text
            )

    return {
        "ok": True
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def home():

    return (
        "<h1>MKOP0 Super Admin</h1>"
        "<p>Super Admin is running.</p>"
    )


@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# =========================================================
# RUN
# =========================================================

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
