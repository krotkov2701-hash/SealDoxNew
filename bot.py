import asyncio
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

# =====================================
# CONFIGURATION
# =====================================

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не установлен!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =====================================
# DATABASE
# =====================================

db = sqlite3.connect("database.db")

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    username TEXT,
    first_seen TEXT,
    last_seen TEXT
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    first_name TEXT,
    username TEXT,
    changed_at TEXT
)
""")

db.commit()


def save_user(user):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    old = db.execute(
        "SELECT first_name, username FROM users WHERE user_id=?",
        (user.id,)
    ).fetchone()

    if old is None:
        db.execute("""
            INSERT INTO users
            VALUES (?, ?, ?, ?, ?)
        """, (
            user.id,
            user.full_name,
            user.username,
            now,
            now
        ))

        db.execute("""
            INSERT INTO history
            (user_id, first_name, username, changed_at)
            VALUES (?, ?, ?, ?)
        """, (user.id, user.full_name, user.username, now))

    else:
        if old != (user.full_name, user.username):
            db.execute("""
                INSERT INTO history
                (user_id, first_name, username, changed_at)
                VALUES (?, ?, ?, ?)
            """, (user.id, user.full_name, user.username, now))

        db.execute("""
            UPDATE users
            SET first_name=?, username=?, last_seen=?
            WHERE user_id=?
        """, (
            user.full_name,
            user.username,
            now,
            user.id
        ))

    db.commit()


# =====================================
# START
# =====================================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🦭 SEAL TRACKER 1.0\n\n"
        "Бот успешно запущен!\n\n"
        "Команды:\n"
        ".rty — карточка пользователя\n"
        "/stats — статистика\n"
        "/history — история наблюдений\n\n"
        "Используй .rty в ответ на сообщение."
    )


# =====================================
# TRACKER
# =====================================

@dp.message(F.text == ".rty")
async def tracker(message: Message):

    if OWNER_ID and message.from_user.id != OWNER_ID:
        return

    if not message.reply_to_message:
        await message.answer(
            "⚠️ Ответь командой .rty на сообщение пользователя."
        )
        return

    target = message.reply_to_message.from_user

    if not target or target.is_bot:
        await message.answer("Не удалось определить пользователя.")
        return

    save_user(target)

    username = (
        f"@{target.username}"
        if target.username else "Не указан"
    )

    first_seen, last_seen = db.execute(
        "SELECT first_seen, last_seen FROM users WHERE user_id=?",
        (target.id,)
    ).fetchone()

    history = db.execute("""
        SELECT first_name, username, changed_at
        FROM history
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 5
    """, (target.id,)).fetchall()

    history_text = ""

    for name, nick, date in history:
        nick = f"@{nick}" if nick else "нет username"

        history_text += (
            f"\n• {name} ({nick})\n"
            f"  {date}\n"
        )

    if not history_text:
        history_text = "\nИстория пока пуста."

    card = (
        "🦭 SEAL TRACKER\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"👤 Имя: {target.full_name}\n"
        f"🔎 Username: {username}\n"
        f"🆔 Telegram ID: {target.id}\n"
        f"📅 Первое обнаружение: {first_seen}\n"
        f"🕒 Последнее обнаружение: {last_seen}\n\n"
        "📊 ИСТОРИЯ ПРОФИЛЯ:\n"
        f"{history_text}\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔒 Телефон и закрытые группы "
        "не доступны через Telegram Bot API."
    )

    try:
        await bot.send_message(
            OWNER_ID or message.from_user.id,
            card
        )

        await message.answer(
            "✅ Карточка отправлена!"
        )

    except Exception:
        await message.answer(
            "⚠️ Не удалось отправить карточку. "
            "Открой личный чат с ботом и нажми /start."
        )


# =====================================
# STATS
# =====================================

@dp.message(Command("stats"))
async def stats(message: Message):

    if OWNER_ID and message.from_user.id != OWNER_ID:
        return

    count = db.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    changes = db.execute(
        "SELECT COUNT(*) FROM history"
    ).fetchone()[0]

    await message.answer(
        "🦭 SEAL TRACKER STATS\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"👥 Профилей: {count}\n"
        f"📝 Записей истории: {changes}"
    )


# =====================================
# HISTORY
# =====================================

@dp.message(Command("history"))
async def history_command(message: Message):

    if OWNER_ID and message.from_user.id != OWNER_ID:
        return

    rows = db.execute("""
        SELECT user_id, first_name, username, changed_at
        FROM history
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

    if not rows:
        await message.answer("История пока пуста.")
        return

    result = "📝 ПОСЛЕДНИЕ НАБЛЮДЕНИЯ\n\n"

    for uid, name, username, date in rows:
        username = f"@{username}" if username else "нет username"

        result += (
            f"👤 {name}\n"
            f"🔎 {username}\n"
            f"🆔 {uid}\n"
            f"📅 {date}\n\n"
        )

    await message.answer(result)


# =====================================
# RUN
# =====================================

async def main():
    print("SEAL TRACKER 1.0 запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
