import os
import secrets
from datetime import datetime, timedelta

import requests
from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    secrets.token_hex(32)
)


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///super_admin.db"
).strip()

# Render may provide postgres://
# SQLAlchemy expects postgresql://
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

SUPER_ADMIN_ID = os.environ.get(
    "SUPER_ADMIN_ID",
    ""
).strip()

APP_URL = os.environ.get(
    "APP_URL",
    "https://telegram-super-admin2.onrender.com"
).strip().rstrip("/")


# =========================================================
# STARTUP LOG
# =========================================================

print("")
print("==========================================")
print("TELEGRAM SUPER ADMIN")
print("APPLICATION STARTING")
print("==========================================")

print(
    "SUPER_ADMIN_TOKEN:",
    "CONFIGURED"
    if SUPER_ADMIN_TOKEN
    else "MISSING"
)

print(
    "SUPER_ADMIN_ID:",
    SUPER_ADMIN_ID
    if SUPER_ADMIN_ID
    else "MISSING"
)

print(
    "APP_URL:",
    APP_URL
)

print(
    "DATABASE:",
    "CONFIGURED"
    if DATABASE_URL
    else "MISSING"
)

print("==========================================")


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


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

with app.app_context():

    try:

        db.create_all()

        print(
            "DATABASE TABLES: READY"
        )

    except Exception as error:

        print(
            "DATABASE ERROR:",
            repr(error)
        )


# =========================================================
# TELEGRAM API - SUPER ADMIN BOT
# =========================================================

def telegram(method, data=None):

    if not SUPER_ADMIN_TOKEN:

        print(
            "TELEGRAM ERROR: "
            "SUPER_ADMIN_TOKEN is missing."
        )

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

        try:

            result = response.json()

        except ValueError:

            print(
                "Telegram returned invalid JSON:",
                response.text
            )

            return None

        print(
            "Telegram result:",
            result
        )

        return result

    except requests.RequestException as error:

        print(
            "Telegram request error:",
            repr(error)
        )

        return None


# =========================================================
# SUPER ADMIN SEND MESSAGE
# =========================================================

def send_message(
    chat_id,
    text,
    keyboard=None
):

    if not chat_id:

        print(
            "SEND MESSAGE ERROR: chat_id missing"
        )

        return None

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
# ANSWER SUPER ADMIN CALLBACK
# =========================================================

def answer_callback(
    callback_id,
    text=""
):

    if not callback_id:

        return None

    return telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id,
            "text": text
        }
    )


# =========================================================
# SUPER ADMIN AUTHORIZATION
# =========================================================

def is_super_admin(chat_id):

    if not SUPER_ADMIN_ID:

        print(
            "SUPER ADMIN ID IS MISSING"
        )

        return False

    result = (
        str(chat_id).strip()
        ==
        str(SUPER_ADMIN_ID).strip()
    )

    print(
        "ADMIN CHECK:",
        chat_id,
        "=>",
        result
    )

    return result


# =========================================================
# SUPER ADMIN MAIN MENU
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

    try:

        bots = ManagedBot.query.order_by(
            ManagedBot.id.desc()
        ).all()

    except Exception as error:

        print(
            "MANAGE BOTS DATABASE ERROR:",
            repr(error)
        )

        send_message(
            chat_id,
            "❌ Kuna tatizo la database."
        )

        return

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

    try:

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

    except Exception as error:

        db.session.rollback()

        print(
            "SETUP SESSION ERROR:",
            repr(error)
        )

        return None


# =========================================================
# ADD BOT
# =========================================================

def add_bot(chat_id):

    setup_token = create_setup_session(
        chat_id
    )

    if not setup_token:

        send_message(
            chat_id,
            "❌ Imeshindikana kutengeneza "
            "secure setup link."
        )

        return

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

        "Tutaunganisha bot mpya kupitia "
        "ukurasa salama.\n\n"

        "🔐 Usitume Bot Token kwenye Telegram chat.\n\n"

        "⏱️ Link hii ni halali kwa dakika 10 tu.\n\n"

        "Bonyeza kitufe hapa chini:",

        keyboard

    )


# =========================================================
# VERIFY BOT TOKEN
# =========================================================

def verify_bot_token(token):

    if not token:

        return None

    try:

        response = requests.get(

            f"https://api.telegram.org/"
            f"bot{token}/getMe",

            timeout=15

        )

        data = response.json()

        print(
            "BOT TOKEN VERIFICATION:",
            response.status_code,
            data
        )

        if not data.get("ok"):

            return None

        return data.get(
            "result"
        )

    except requests.RequestException as error:

        print(
            "BOT TOKEN REQUEST ERROR:",
            repr(error)
        )

        return None

    except ValueError:

        return None


# =========================================================
# MANAGED BOT TELEGRAM API
# =========================================================

def managed_telegram(
    bot,
    method,
    data=None
):

    if not bot:

        print(
            "MANAGED TELEGRAM ERROR: "
            "Bot object missing."
        )

        return None

    if not bot.token:

        print(
            "MANAGED TELEGRAM ERROR: "
            "Bot token missing."
        )

        return None

    url = (
        "https://api.telegram.org/"
        f"bot{bot.token}/{method}"
    )

    try:

        response = requests.post(

            url,

            json=data or {},

            timeout=20

        )

        try:

            result = response.json()

        except ValueError:

            print(
                "MANAGED BOT INVALID JSON:",
                response.text
            )

            return None

        print(

            f"MANAGED BOT #{bot.id} "
            f"{method}: "
            f"{response.status_code}"

        )

        print(
            "RESULT:",
            result
        )

        return result

    except requests.RequestException as error:

        print(
            "MANAGED TELEGRAM ERROR:",
            repr(error)
        )

        return None


# =========================================================
# SEND MESSAGE FROM MANAGED BOT
# =========================================================

def managed_send_message(
    bot,
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

    return managed_telegram(

        bot,

        "sendMessage",

        payload

    )


# =========================================================
# SET WEBHOOK FOR MANAGED BOT
# =========================================================

def set_managed_bot_webhook(bot):

    webhook_url = (

        f"{APP_URL}/telegram/bot/"
        f"{bot.id}/webhook"

    )

    print(
        f"SETTING WEBHOOK FOR BOT #{bot.id}:",
        webhook_url
    )

    result = managed_telegram(

        bot,

        "setWebhook",

        {
            "url": webhook_url
        }

    )

    return result


# =========================================================
# GET MANAGED BOT WEBHOOK INFO
# =========================================================

def get_managed_bot_webhook_info(bot):

    return managed_telegram(
        bot,
        "getWebhookInfo"
    )


# =========================================================
# MANAGED BOT MENU
# =========================================================

def managed_bot_menu(
    bot,
    chat_id
):

    keyboard = {

        "inline_keyboard": [

            [
                {
                    "text": "📋 Menu",
                    "callback_data": "bot_menu"
                }
            ],

            [
                {
                    "text": "ℹ️ Help",
                    "callback_data": "bot_help"
                }
            ]

        ]

    }

    managed_send_message(

        bot,

        chat_id,

        f"🤖 Karibu kwenye {bot.name}.\n\n"

        "Bot iko tayari kupokea huduma zako.\n\n"

        "Chagua huduma hapa chini:",

        keyboard

    )


# =========================================================
# MANAGED BOT HELP
# =========================================================

def managed_bot_help(
    bot,
    chat_id
):

    managed_send_message(

        bot,

        chat_id,

        "ℹ️ HELP\n\n"

        "Tumia /start kufungua menu kuu.\n"

        "Tumia /help kupata msaada.\n\n"

        "Kwa huduma zaidi, "
        "chagua huduma kwenye menu."

    )


# =========================================================
# NOTIFY SUPER ADMIN
# =========================================================

def notify_super_admin(

    bot,
    chat_id,
    username,
    text

):

    if not SUPER_ADMIN_ID:

        print(
            "SUPER ADMIN NOTIFICATION SKIPPED:"
            " SUPER_ADMIN_ID missing."
        )

        return

    username_text = (

        f"@{username}"

        if username

        else "-"

    )

    notification = (

        "🔔 MANAGED BOT ACTIVITY\n\n"

        f"🤖 Bot: {bot.name}\n"

        f"🆔 Bot ID: #{bot.id}\n"

        f"👤 User: {username_text}\n"

        f"💬 Chat ID: {chat_id}\n\n"

        "📩 Message:\n"

        f"{text}"

    )

    send_message(

        SUPER_ADMIN_ID,

        notification

    )


# =========================================================
# PROCESS MANAGED BOT UPDATE
# =========================================================

def process_managed_bot_update(

    bot,
    update

):

    print("")
    print("==========================================")
    print(
        f"MANAGED BOT UPDATE #{bot.id}"
    )
    print(update)
    print("==========================================")

    # =====================================================
    # NORMAL MESSAGE
    # =====================================================

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

        user = message.get(
            "from",
            {}
        )

        username = user.get(
            "username",
            ""
        )

        first_name = user.get(
            "first_name",
            ""
        )

        text = message.get(
            "text",
            ""
        ).strip()

        # -------------------------------------------------
        # /START
        # -------------------------------------------------

        if text.startswith(
            "/start"
        ):

            managed_bot_menu(

                bot,

                chat_id

            )

        # -------------------------------------------------
        # /HELP
        # -------------------------------------------------

        elif text.startswith(
            "/help"
        ):

            managed_bot_help(

                bot,

                chat_id

            )

        # -------------------------------------------------
        # OTHER MESSAGE
        # -------------------------------------------------

        else:

            managed_send_message(

                bot,

                chat_id,

                "✅ Ujumbe wako umepokelewa.\n\n"

                "Tafadhali tumia /start "
                "kufungua menu kuu."

            )

        # -------------------------------------------------
        # NOTIFY SUPER ADMIN
        # -------------------------------------------------

        notify_super_admin(

            bot,

            chat_id,

            username,

            text or "[message without text]"

        )

        return

    # =====================================================
    # CALLBACK QUERY
    # =====================================================

    callback = update.get(
        "callback_query"
    )

    if not callback:

        print(
            "MANAGED UPDATE HAS NO MESSAGE "
            "OR CALLBACK."
        )

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

    managed_telegram(

        bot,

        "answerCallbackQuery",

        {
            "callback_query_id":
                callback_id
        }

    )

    if data == "bot_menu":

        managed_bot_menu(

            bot,

            chat_id

        )

    elif data == "bot_help":

        managed_bot_help(

            bot,

            chat_id

        )

    else:

        print(
            "UNKNOWN MANAGED CALLBACK:",
            data
        )


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

        db.session.delete(
            setup
        )

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

                error=(
                    "Tafadhali weka jina la bot."
                )

            )

        if not token:

            return render_template(

                "setup.html",

                error=(
                    "Tafadhali weka Bot Token."
                )

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

        try:

            bot = ManagedBot(

                name=name,

                username=username,

                token=token,

                status="CONNECTED"

            )

            db.session.add(
                bot
            )

            db.session.delete(
                setup
            )

            db.session.commit()

        except Exception as error:

            db.session.rollback()

            print(
                "SAVE BOT ERROR:",
                repr(error)
            )

            return render_template(

                "setup.html",

                error=(

                    "❌ Imeshindikana kuhifadhi "
                    "bot kwenye database."

                )

            )

        # -------------------------------------------------
        # AUTOMATICALLY SET BOT WEBHOOK
        # -------------------------------------------------

        webhook_result = (
            set_managed_bot_webhook(
                bot
            )
        )

        print(
            "NEW BOT WEBHOOK RESULT:",
            webhook_result
        )

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
            "kwenye Super Admin.\n\n"

            "🔗 Webhook imewekwa "
            "moja kwa moja."

        )

        return render_template(

            "connected.html",

            bot=bot

        )

    return render_template(
        "setup.html"
    )


# =========================================================
# MANAGED BOT WEBHOOK
# =========================================================

@app.route(
    "/telegram/bot/<int:bot_id>/webhook",
    methods=["POST"]
)
def managed_bot_webhook(bot_id):

    print("")
    print("==========================================")
    print(
        f"MANAGED BOT WEBHOOK #{bot_id}"
    )
    print("==========================================")

    try:

        bot = db.session.get(
            ManagedBot,
            bot_id
        )

    except Exception as error:

        print(
            "DATABASE LOOKUP ERROR:",
            repr(error)
        )

        return jsonify({

            "ok": False,

            "error": "Database error"

        }), 500

    if not bot:

        print(
            "MANAGED BOT NOT FOUND:",
            bot_id
        )

        return jsonify({

            "ok": False,

            "error": "Bot not found"

        }), 404

    update = request.get_json(
        silent=True
    )

    if not update:

        print(
            "INVALID MANAGED BOT UPDATE"
        )

        return jsonify({

            "ok": False,

            "error": "Invalid update"

        }), 400

    try:

        process_managed_bot_update(

            bot,

            update

        )

    except Exception as error:

        print(
            "MANAGED BOT PROCESSING ERROR:",
            repr(error)
        )

    return jsonify({

        "ok": True

    }), 200


# =========================================================
# ACTIVATE ALL CONNECTED BOT WEBHOOKS
# =========================================================

def activate_all_managed_bots():

    try:

        bots = ManagedBot.query.filter_by(
            status="CONNECTED"
        ).all()

    except Exception as error:

        print(
            "COULD NOT LOAD MANAGED BOTS:",
            repr(error)
        )

        return

    if not bots:

        print(
            "NO MANAGED BOTS TO ACTIVATE."
        )

        return

    print(
        f"ACTIVATING {len(bots)} MANAGED BOT(S)"
    )

    for bot in bots:

        try:

            result = set_managed_bot_webhook(
                bot
            )

            print(

                f"BOT #{bot.id} "
                f"WEBHOOK RESULT:",
                result

            )

        except Exception as error:

            print(

                f"BOT #{bot.id} "
                "WEBHOOK ERROR:",
                repr(error)

            )


# =========================================================
# SUPER ADMIN TELEGRAM UPDATE
# =========================================================

def process_update(update):

    print("")
    print("==========================================")
    print("SUPER ADMIN TELEGRAM UPDATE")
    print(update)
    print("==========================================")

    # =====================================================
    # NORMAL MESSAGE
    # =====================================================

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

                "⛔ Huna ruhusa ya kutumia "
                "bot hii."

            )

            return

        text = message.get(
            "text",
            ""
        ).strip()

        print(
            "SUPER ADMIN MESSAGE:",
            text
        )

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

                "🟢 Super Admin Bot iko hai.\n\n"

                f"🆔 Your ID: {chat_id}\n"

                f"👑 Admin ID: "
                f"{SUPER_ADMIN_ID}"

            )

            return

        main_menu(
            chat_id
        )

        return

    # =====================================================
    # CALLBACK QUERY
    # =====================================================

    callback = update.get(
        "callback_query"
    )

    if not callback:

        print(
            "UPDATE HAS NO MESSAGE "
            "OR CALLBACK."
        )

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

    else:

        print(
            "UNKNOWN SUPER ADMIN CALLBACK:",
            data
        )


# =========================================================
# SUPER ADMIN WEBHOOK
# =========================================================

@app.route(
    "/telegram/webhook",
    methods=["POST"]
)
def telegram_webhook():

    print("")
    print("==========================================")
    print("SUPER ADMIN WEBHOOK RECEIVED")
    print("==========================================")

    try:

        update = request.get_json(
            silent=True
        )

        if not update:

            return jsonify({

                "ok": False,

                "error": "Invalid update"

            }), 400

        process_update(
            update
        )

        return jsonify({

            "ok": True

        }), 200

    except Exception as error:

        print(
            "SUPER ADMIN WEBHOOK ERROR:",
            repr(error)
        )

        return jsonify({

            "ok": True,

            "processed": False

        }), 200


# =========================================================
# SUPER ADMIN WEBHOOK GET TEST
# =========================================================

@app.route(
    "/telegram/webhook",
    methods=["GET"]
)
def webhook_get():

    return jsonify({

        "status": "ok",

        "message": (
            "Telegram webhook endpoint "
            "is active."
        ),

        "method": "POST",

        "endpoint": "/telegram/webhook"

    })


# =========================================================
# SET SUPER ADMIN WEBHOOK
# =========================================================

def set_super_admin_webhook():

    if not SUPER_ADMIN_TOKEN:

        print(
            "SUPER ADMIN WEBHOOK SKIPPED: "
            "token missing."
        )

        return None

    webhook_url = (
        f"{APP_URL}/telegram/webhook"
    )

    print(
        "SETTING SUPER ADMIN WEBHOOK:",
        webhook_url
    )

    return telegram(

        "setWebhook",

        {
            "url": webhook_url
        }

    )


# =========================================================
# WEBHOOK INFORMATION
# =========================================================

@app.route(
    "/webhook-info",
    methods=["GET"]
)
def webhook_info():

    result = telegram(
        "getWebhookInfo"
    )

    if result is None:

        return jsonify({

            "ok": False,

            "error": (
                "Could not contact Telegram."
            )

        }), 500

    return jsonify(
        result
    )


# =========================================================
# BOT INFORMATION
# =========================================================

@app.route(
    "/bot-info",
    methods=["GET"]
)
def bot_info():

    result = telegram(
        "getMe"
    )

    if result is None:

        return jsonify({

            "ok": False,

            "error": (
                "Telegram token missing "
                "or Telegram API unavailable."
            )

        }), 500

    return jsonify(
        result
    )


# =========================================================
# MANAGED BOT INFORMATION
# =========================================================

@app.route(
    "/managed-bot/<int:bot_id>/webhook-info",
    methods=["GET"]
)
def managed_bot_webhook_info(bot_id):

    bot = db.session.get(
        ManagedBot,
        bot_id
    )

    if not bot:

        return jsonify({

            "ok": False,

            "error": "Bot not found"

        }), 404

    result = get_managed_bot_webhook_info(
        bot
    )

    if result is None:

        return jsonify({

            "ok": False,

            "error": (
                "Could not contact Telegram."
            )

        }), 500

    return jsonify(
        result
    )


# =========================================================
# MANAGED BOT TEST PAGE
# =========================================================

@app.route(
    "/managed-bot/<int:bot_id>",
    methods=["GET"]
)
def managed_bot_page(bot_id):

    bot = db.session.get(
        ManagedBot,
        bot_id
    )

    if not bot:

        return jsonify({

            "ok": False,

            "error": "Bot not found"

        }), 404

    return jsonify({

        "ok": True,

        "bot_id": bot.id,

        "name": bot.name,

        "username": bot.username,

        "status": bot.status,

        "webhook": (
            f"{APP_URL}/telegram/bot/"
            f"{bot.id}/webhook"
        )

    })


# =========================================================
# DASHBOARD
# =========================================================

def dashboard(chat_id):

    try:

        total = ManagedBot.query.count()

        connected = ManagedBot.query.filter_by(
            status="CONNECTED"
        ).count()

        disconnected = ManagedBot.query.filter_by(
            status="DISCONNECTED"
        ).count()

    except Exception as error:

        print(
            "DASHBOARD DATABASE ERROR:",
            repr(error)
        )

        send_message(
            chat_id,
            "❌ Kuna tatizo la database."
        )

        return

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

        "🔐 Token configuration: "
        f"{'ACTIVE' if SUPER_ADMIN_TOKEN else 'MISSING'}",

        keyboard

    )


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

    max-width:650px;

    margin:60px auto;

    background:#1d2935;

    padding:35px;

    border-radius:20px;

}

.ok {

    color:#35d07f;

    font-weight:bold;

}

a {

    color:#35d07f;

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
Telegram Super Admin system is online.
</p>

<p>
Super Admin webhook:
<strong>/telegram/webhook</strong>
</p>

<p>
Managed bot webhook:
<strong>/telegram/bot/&lt;bot_id&gt;/webhook</strong>
</p>

<hr>

<p>
<a href="/health">
Health Check
</a>
</p>

<p>
<a href="/webhook-info">
Super Admin Webhook Info
</a>
</p>

<p>
<a href="/bot-info">
Super Admin Bot Info
</a>
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

    try:

        bot_count = ManagedBot.query.count()

    except Exception:

        bot_count = None

    return jsonify({

        "status": "ok",

        "service": "telegram-super-admin",

        "webhook": "/telegram/webhook",

        "token_configured": bool(
            SUPER_ADMIN_TOKEN
        ),

        "admin_id_configured": bool(
            SUPER_ADMIN_ID
        ),

        "database_configured": bool(
            DATABASE_URL
        ),

        "managed_bots": bot_count

    })


# =========================================================
# 404
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({

        "error": "Not Found",

        "status": 404

    }), 404


# =========================================================
# 500
# =========================================================

@app.errorhandler(500)
def server_error(error):

    return jsonify({

        "error": "Internal Server Error",

        "status": 500

    }), 500


# =========================================================
# APPLICATION STARTUP
# =========================================================

def startup():

    print("")
    print("==========================================")
    print("APPLICATION STARTUP")
    print("==========================================")

    # -----------------------------------------------------
    # SUPER ADMIN TOKEN
    # -----------------------------------------------------

    if not SUPER_ADMIN_TOKEN:

        print(
            "WARNING: SUPER_ADMIN_TOKEN "
            "IS NOT CONFIGURED."
        )

    # -----------------------------------------------------
    # SUPER ADMIN ID
    # -----------------------------------------------------

    if not SUPER_ADMIN_ID:

        print(
            "WARNING: SUPER_ADMIN_ID "
            "IS NOT CONFIGURED."
        )

    # -----------------------------------------------------
    # SUPER ADMIN BOT
    # -----------------------------------------------------

    if SUPER_ADMIN_TOKEN:

        try:

            result = telegram(
                "getMe"
            )

            if result and result.get(
                "ok"
            ):

                bot_info_data = result.get(
                    "result",
                    {}
                )

                print(
                    "SUPER ADMIN BOT:",
                    bot_info_data.get(
                        "first_name"
                    )
                )

                print(
                    "BOT USERNAME:",
                    bot_info_data.get(
                        "username"
                    )
                )

                # -----------------------------------------
                # SET SUPER ADMIN WEBHOOK
                # -----------------------------------------

                webhook_result = (
                    set_super_admin_webhook()
                )

                print(
                    "SUPER ADMIN WEBHOOK RESULT:",
                    webhook_result
                )

            else:

                print(
                    "WARNING: Telegram getMe failed."
                )

        except Exception as error:

            print(
                "SUPER ADMIN STARTUP ERROR:",
                repr(error)
            )

    # -----------------------------------------------------
    # ACTIVATE EXISTING MANAGED BOTS
    # -----------------------------------------------------

    try:

        activate_all_managed_bots()

    except Exception as error:

        print(
            "MANAGED BOT STARTUP ERROR:",
            repr(error)
        )

    print("==========================================")
    print("APPLICATION READY")
    print("==========================================")
    print("")


# =========================================================
# RUN STARTUP
# =========================================================

startup()


# =========================================================
# LOCAL DEVELOPMENT
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

        port=port,

        debug=False

    )
