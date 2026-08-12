
import os
import sqlite3
import requests

from flask import Flask, jsonify

app = Flask(__name__)

DB = "super_admin.db"

SUPER_ADMIN_BOT_TOKEN = os.environ.get("SUPER_ADMIN_BOT_TOKEN")
SUPER_ADMIN_ID = os.environ.get("SUPER_ADMIN_ID")


def db():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT,
            token TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE'
        )
    """)

    connection.commit()
    connection.close()


def telegram(method, data=None):
    if not SUPER_ADMIN_BOT_TOKEN:
        return None

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{SUPER_ADMIN_BOT_TOKEN}/{method}",
            json=data or {},
            timeout=15
        )

        return response.json()

    except requests.RequestException:
        return None


def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    return telegram("sendMessage", payload)


def main_menu():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🤖 Manage Bots",
                    "callback_data": "bots"
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


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "service": "Telegram Super Admin"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok"
    })


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():

    update = request_json()

    if not update:
        return {"ok": True}

    message = update.get("message")

    if message:

        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))

        # Only the Super Admin can control the system
        if not SUPER_ADMIN_ID or chat_id != str(SUPER_ADMIN_ID):
            return {"ok": True}

        text = message.get("text", "").strip()

        if text == "/start":

            send_message(
                chat_id,
                "👑 SUPER ADMIN PANEL\n\n"
                "Karibu kwenye mfumo mkuu wa usimamizi wa bots.\n\n"
                "Chagua huduma:",
                main_menu()
            )

        elif text == "/bots":

            show_bots(chat_id)

        elif text == "/dashboard":

            show_dashboard(chat_id)

        else:

            send_message(
                chat_id,
                "👑 SUPER ADMIN\n\n"
                "Chagua huduma kutoka kwenye menu.",
                main_menu()
            )

    callback = update.get("callback_query")

    if callback:

        handle_callback(callback)

    return {"ok": True}


def request_json():
    from flask import request

    return request.get_json(silent=True) or {}


def show_bots(chat_id):

    connection = db()

    bots = connection.execute(
        "SELECT * FROM bots ORDER BY id DESC"
    ).fetchall()

    connection.close()

    if not bots:

        text = (
            "🤖 CONNECTED BOTS\n\n"
            "Hakuna bot iliyounganishwa bado."
        )

    else:

        lines = ["🤖 CONNECTED BOTS\n"]

        for bot in bots:

            lines.append(
                f"{bot['id']}. {bot['name']}\n"
                f"Username: @{bot['username'] or '-'}\n"
                f"Status: {bot['status']}\n"
            )

        text = "\n".join(lines)

    send_message(chat_id, text, {
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
                    "callback_data": "bots"
                }
            ],
            [
                {
                    "text": "⬅️ Main Menu",
                    "callback_data": "main"
                }
            ]
        ]
    })


def show_dashboard(chat_id):

    connection = db()

    total = connection.execute(
        "SELECT COUNT(*) AS total FROM bots"
    ).fetchone()["total"]

    active = connection.execute(
        "SELECT COUNT(*) AS total FROM bots WHERE status='ACTIVE'"
    ).fetchone()["total"]

    connection.close()

    text = (
        "📊 SUPER ADMIN DASHBOARD\n\n"
        f"🤖 Total Bots: {total}\n"
        f"🟢 Active Bots: {active}\n"
        f"🔴 Inactive Bots: {total - active}\n"
    )

    send_message(chat_id, text, main_menu())


def handle_callback(callback):

    callback_id = callback.get("id")

    message = callback.get("message", {})
    chat = message.get("chat", {})

    chat_id = str(chat.get("id", ""))

    # Security check
    if not SUPER_ADMIN_ID:
        return

    if chat_id != str(SUPER_ADMIN_ID):
        return

    data = callback.get("data", "")

    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )

    if data == "main":

        send_message(
            chat_id,
            "👑 SUPER ADMIN PANEL",
            main_menu()
        )

    elif data == "bots":

        show_bots(chat_id)

    elif data == "dashboard":

        show_dashboard(chat_id)

    elif data == "notifications":

        send_message(
            chat_id,
            "🔔 NOTIFICATIONS\n\n"
            "Notification management itaongezwa kwenye hatua inayofuata.",
            main_menu()
        )

    elif data == "settings":

        send_message(
            chat_id,
            "⚙️ SETTINGS\n\n"
            "System settings itaongezwa kwenye hatua inayofuata.",
            main_menu()
        )

    elif data == "add_bot":

        send_message(
            chat_id,
            "➕ ADD BOT\n\n"
            "Hatua inayofuata tutaongeza mfumo salama wa "
            "ku-register bot mpya bila kuweka token kwenye chat."
        )


init_db()


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
