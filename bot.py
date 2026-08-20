import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice
)

# Инициализация бота и базы данных
TOKEN = "8983343344:AAFk61fK5vLB7yn1k90P0MtTAbenRyobBcI"  # Токен подтянется из переменных окружения на Railway
bot = Bot(token=TOKEN)
router = Router()
dp = Dispatcher()

# Подключение к БД
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц, если их нет
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 100,
    vip_expires TEXT,
    last_daily TEXT,
    referrer INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS promos (
    code TEXT PRIMARY KEY,
    reward INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS used_promos (
    user_id INTEGER,
    code TEXT,
    PRIMARY KEY (user_id, code)
)
""")
conn.commit()

def get_user_data(user_id):
    cursor.execute("SELECT balance, vip_expires, last_daily FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, 100)", (user_id,))
        conn.commit()
        return 100, None, None
    return row[0], row[1], row[2]

def is_vip(vip_expires):
    if not vip_expires:
        return False
    return datetime.fromisoformat(vip_expires) > datetime.now()


# --- ГЛАВНОЕ МЕНЮ И СТАРТ ---
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Ежедневная Награда", callback_data="daily_reward")],
        [InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="ref_link")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])

@router.message(Command("start"))
@router.message(F.text.lower() == "старт")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    get_user_data(user_id) # Регистрация в базе при старте

    # Обработка рефералки при старте (если перешли по ссылке /start 123456)
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            cursor.execute("SELECT referrer FROM users WHERE user_id = ?", (user_id,))
            res = cursor.fetchone()
            if res and not res[0]:
                cursor.execute("UPDATE users SET referrer = ? WHERE user_id = ?", (ref_id, user_id))
                cursor.execute("UPDATE users SET balance = balance + 50 WHERE user_id = ?", (ref_id,))
                conn.commit()
                try:
                    await bot.send_message(ref_id, "🎉 По вашей ссылке зарегистрирован новый игрок! Вам начислено 50 монет.")
                except:
                    pass

    await message.answer("Привет! Выбери кнопку ниже", reply_markup=get_main_keyboard())


# --- КНОПКИ МЕНЮ (КОЛБЭКИ) ---
@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    bal, vip_exp, _ = get_user_data(user_id)
    vip_status = "💎 VIP Активен" if is_vip(vip_exp) else "Обычный"

    text = (
        f"👤 **Ваш профиль:**\n"
        f"🆔 ID: `{user_id}`\n"
        f"💰 Баланс: `{bal}` монет\n"
        f"🌟 Статус: {vip_status}"
    )
    await callback.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "daily_reward")
async def cb_daily(callback: CallbackQuery):
    user_id = callback.from_user.id
    _, _, last_daily = get_user_data(user_id)

    now = datetime.now()
    if last_daily:
        last_date = datetime.fromisoformat(last_daily)
        if now - last_date < timedelta(days=1):
            timeLeft = timedelta(days=1) - (now - last_date)
            hours, remainder = divmod(int(timeLeft.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            return await callback.answer(f"⏳ Награда будет доступна через {hours}ч. {minutes}мин.", show_alert=True)

    cursor.execute("UPDATE users SET balance = balance + 50, last_daily = ? WHERE user_id = ?", (now.isoformat(), user_id))
    conn.commit()
    await callback.answer("✅ Вы получили ежедневную награду: 50 монет!", show_alert=True)


@router.callback_query(F.data == "ref_link")
async def cb_ref(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    await callback.message.edit_text(
        f"🔗 **Ваша реферальная ссылка:**\n`{link}`\n\nПриглашайте друзей и получайте по 50 монет за каждого!",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


# --- ЕДИНЫЙ ОБРАБОТЧИК ТЕКСТОВЫХ КОМАНД БЕЗ СЛЭША ---
@router.message(F.text)
async def text_commands_router(message: Message):
    if not message.text:
        return

    text_lower = message.text.lower().strip()
    parts = text_lower.split()
    if not parts:
        return

    cmd = parts[0]
    user_id = message.from_user.id

    # 1. Баланс
    if cmd in ("б", "баланс"):
        bal, _, _ = get_user_data(user_id)
        return await message.answer(f"💰 Ваш баланс: `{bal}` монет", parse_mode="Markdown")

    # 2. Паспорт
    elif cmd == "паспорт":
        bal, vip_exp, _ = get_user_data(user_id)
        vip_status = "💎 VIP Активен" if is_vip(vip_exp) else "Обычный"
        text = (
            f"📜 **Паспорт игрока:**\n"
            f"👤 Имя: {message.from_user.first_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💰 Монеты: `{bal}`\n"
            f"🌟 Уровень: {vip_status}"
        )
        return await message.answer(text, parse_mode="Markdown")

    # 3. Промокоды
    elif cmd == "промо":
        if len(parts) < 2:
            return await message.answer("❌ Укажите код промокода. Пример: `промо START`", parse_mode="Markdown")
        code = parts[1].upper()

        cursor.execute("SELECT reward FROM promos WHERE code = ?", (code,))
        promo = cursor.fetchone()
        if not promo:
            return await message.answer("❌ Такого промокода не существует.")

        reward = promo[0]
        cursor.execute("SELECT * FROM used_promos WHERE user_id = ? AND code = ?", (user_id, code))
        if cursor.fetchone():
            return await message.answer("❌ Вы уже активировали этот промокод!")

        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
        cursor.execute("INSERT INTO used_promos (user_id, code) VALUES (?, ?)", (user_id, code))
        conn.commit()
        return await message.answer(f"✅ Промокод успешно активирован! Вам зачислено: `{reward}` монет.", parse_mode="Markdown")

    # 4. Слоты
    elif cmd == "слоты":
        if len(parts) < 2 or not parts[1].isdigit():
            return await message.answer("❌ Формат: `слоты <ставка>`", parse_mode="Markdown")
        bet = int(parts[1])
        if bet < 5:
            return await message.answer("❌ Минимальная ставка — 5 монет.")

        bal, vip_exp, _ = get_user_data(user_id)
        if bal < bet:
            return await message.answer(f"❌ Мало монет на балансе! У вас: {bal}, а ставка: {bet}")

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
        conn.commit()

        msg = await message.answer_dice("🎰")
        await asyncio.sleep(2.5)

        if msg.dice.value in [1, 22, 43, 64]:
            win = (bet * 5) * (2 if is_vip(vip_exp) else 1)
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, user_id))
            await message.answer(f"🎰 **ДЖЕКПОТ!** Выиграл `{win}` монет!", parse_mode="Markdown")
        else:
            await message.answer("😢 Мимо, бро. Повезет в следующий раз.")
        conn.commit()

    # 5. Кости
    elif cmd == "кости":
        if len(parts) < 2 or not parts[1].isdigit():
            return await message.answer("❌ Формат: `кости <ставка>`", parse_mode="Markdown")
        bet = int(parts[1])
        if bet < 5:
            return await message.answer("❌ Минимальная ставка — 5 монет.")

        bal, vip_exp, _ = get_user_data(user_id)
        if bal < bet:
            return await message.answer(f"❌ Мало монет на балансе! У вас: {bal}, а ставка: {bet}")

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
        conn.commit()

        msg = await message.answer_dice("🎲")
        await asyncio.sleep(3)

        if msg.dice.value >= 4:
            win = (bet * 2) * (2 if is_vip(vip_exp) else 1)
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, user_id))
            await message.answer(f"🎯 Выпало {msg.dice.value}! Забирай выигрыш: `{win}` монет!", parse_mode="Markdown")
        else:
            await message.answer(f"😢 Выпало {msg.dice.value}. Луз.")
        conn.commit()

    # 6. Мины
    elif cmd == "мины":
        if len(parts) < 2 or not parts[1].isdigit():
            return await message.answer("❌ Формат: `мины <ставка>`", parse_mode="Markdown")
        bet = int(parts[1])
        if bet < 5:
            return await message.answer("❌ Минимальная ставка — 5 монет.")

        bal, vip_exp, _ = get_user_data(user_id)
        if bal < bet:
            return await message.answer(f"❌ Мало монет на балансе! У вас: {bal}, а ставка: {bet}")

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
        conn.commit()

        chance = 0.25 - (0.15 if is_vip(vip_exp) else 0)
        if random.random() > chance:
            win = int(bet * 2) * (2 if is_vip(vip_exp) else 1)
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, user_id))
            await message.answer(f"💰 **Изи катка!** Поле чистое. Выигрыш: `{win}` монет!", parse_mode="Markdown")
        else:
            await message.answer("💥 **БУХ!** Нарвался на мину, луз.", parse_mode="Markdown")
        conn.commit()


# Запуск бота
async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

