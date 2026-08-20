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
    PreCheckoutQuery,
    LabeledPrice
)

# Инициализация бота
TOKEN = "8983343344:AAFSfWIZdeqOffaycVrhU5TWC0eTA9FSpRU"
bot = Bot(token=TOKEN)
router = Router()
dp = Dispatcher()

# Инициализация базы данных
def init_db():
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
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

init_db()

def get_user_data(user_id):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
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


# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Казино", callback_data="menu_casino")],
        [InlineKeyboardButton(text="🛒 Магазин (Монеты / VIP)", callback_data="menu_shop")],
        [InlineKeyboardButton(text="🎁 Ежедневная Награда", callback_data="daily_reward")],
        [InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="ref_link")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])

def get_casino_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Слоты", callback_data="game_slots_info"),
         InlineKeyboardButton(text="🎲 Кости", callback_data="game_dice_info")],
        [InlineKeyboardButton(text="💣 Мины", callback_data="game_mines_info")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_main")]
    ])

def get_shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Купить 500 монет", callback_data="buy_coins")],
        [InlineKeyboardButton(text="💎 Купить VIP на 30 дней", callback_data="buy_vip")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_main")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])


# --- СТАРТ (Только для ЛС) ---
@router.message(Command("start"))
@router.message(F.text.lower() == "старт")
async def cmd_start(message: Message):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    get_user_data(user_id)

    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            with sqlite3.connect("database.db") as conn:
                cursor = conn.cursor()
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

    await message.answer("Привет! Выбери нужный раздел в меню:", reply_markup=get_main_keyboard())


# --- КОЛБЭКИ (МЕНЮ И МАГАЗИН) ---
@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text("Привет! Выбери нужный раздел в меню:", reply_markup=get_main_keyboard())
    except:
        pass


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    bal, vip_exp, _ = get_user_data(user_id)
    vip_status = "💎 VIP Активен" if is_vip(vip_exp) else "Обычный"

    text = (
        f"👤 **Ваш профиль:**\n"
        f"🆔 ID: `{user_id}`\n"
        f"💰 Баланс: `{bal}` монет\n"
        f"🌟 Статус: {vip_status}"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    except:
        pass


@router.callback_query(F.data == "menu_casino")
async def cb_menu_casino(callback: CallbackQuery):
    await callback.answer()
    text = (
        f"🎰 **Игровое казино:**\n\n"
        f"Выбирай игру или пиши в чат команды:\n"
        f"• `слоты <ставка>`\n"
        f"• `кости <ставка>`\n"
        f"• `мины <ставка>`"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_casino_keyboard(), parse_mode="Markdown")
    except:
        pass


@router.callback_query(F.data == "menu_shop")
async def cb_menu_shop(callback: CallbackQuery):
    await callback.answer()
    text = (
        f"🛒 **Магазин привилегий:**\n\n"
        f"• **500 монет** — для поднятия капитала\n"
        f"• **VIP статус (30 дней)** — удваивает выигрыши в казино и снижает шанс луза в минах!"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_shop_keyboard(), parse_mode="Markdown")
    except:
        pass


@router.callback_query(F.data.in_({"game_slots_info", "game_dice_info", "game_mines_info"}))
async def cb_game_info(callback: CallbackQuery):
    games = {
        "game_slots_info": "слоты <ставка> (например: слоты 50)",
        "game_dice_info": "кости <ставка> (например: кости 50)",
        "game_mines_info": "мины <ставка> (например: мины 50)"
    }
    await callback.answer(f"Напиши в чат команду: {games.get(callback.data)}", show_alert=True)


# --- ПОКУПКИ (ИНВОЙСЫ) ---
@router.callback_query(F.data == "buy_coins")
async def cb_buy_coins(callback: CallbackQuery):
    await callback.answer()
    prices = [LabeledPrice(label="500 монет", amount=100)]
    await callback.message.answer_invoice(
        title="Покупка монет",
        description="Зачисление 500 монет на баланс бота",
        payload="coins_500",
        provider_token="",
        currency="XTR",
        prices=prices
    )

@router.callback_query(F.data == "buy_vip")
async def cb_buy_vip(callback: CallbackQuery):
    await callback.answer()
    prices = [LabeledPrice(label="VIP Статус (30 дней)", amount=300)]
    await callback.message.answer_invoice(
        title="VIP Статус",
        description="Активация VIP привилегий на 30 дней",
        payload="vip_30_days",
        provider_token="",
        currency="XTR",
        prices=prices
    )

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payment = message.successful_payment
    user_id = message.from_user.id

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        if payment.invoice_payload == "coins_500":
            cursor.execute("UPDATE users SET balance = balance + 500 WHERE user_id = ?", (user_id,))
            conn.commit()
            await message.answer("✅ Успешно! Вам зачислено 500 монет.")
        elif payment.invoice_payload == "vip_30_days":
            new_vip_date = (datetime.now() + timedelta(days=30)).isoformat()
            cursor.execute("UPDATE users SET vip_expires = ? WHERE user_id = ?", (new_vip_date, user_id))
            conn.commit()
            await message.answer("💎 Успешно! VIP-статус активирован на 30 дней.")


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

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + 50, last_daily = ? WHERE user_id = ?", (now.isoformat(), user_id))
        conn.commit()

    await callback.answer("✅ Вы получили ежедневную награду: 50 монет!", show_alert=True)


@router.callback_query(F.data == "ref_link")
async def cb_ref(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    try:
        await callback.message.edit_text(
            f"🔗 **Ваша реферальная ссылка:**\n`{link}`\n\nПриглашайте друзей и получайте по 50 монет за каждого!",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
    except:
        pass


# --- ТЕКСТОВЫЕ КОМАНДЫ И ИГРЫ ---
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

    # 3. Перевод монет другому игроку
    elif cmd in ("передать", "перевод", "pay"):
        if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
            return await message.answer("❌ Формат: `передать <айди> <сумма>`", parse_mode="Markdown")

        target_id = int(parts[1])
        amount = int(parts[2])

        if amount <= 0:
            return await message.answer("❌ Сумма перевода должна быть больше нуля.")
        if target_id == user_id:
            return await message.answer("❌ Нельзя переводить монеты самому себе!")

        bal, _, _ = get_user_data(user_id)
        if bal < amount:
            return await message.answer(f"❌ Недостаточно монет! Ваш баланс: `{bal}` монет.", parse_mode="Markdown")

        # Проверяем, существует ли получатель в БД (хотя бы раз запускал бота)
        target_bal, _, _ = get_user_data(target_id)

        commission = int(amount * 0.10) # Комиссия 10%
        final_amount = amount - commission # Сколько дойдет до получателя

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            # Списываем всю сумму у отправителя
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
            # Зачисляем сумму с учетом комиссии получателю
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (final_amount, target_id))
            conn.commit()

        return await message.answer(
            f"✅ Успешный перевод!\n"
            f"📤 Списано с учетом комиссии (10%): `{amount}` монет\n"
            f"📥 Получателю зачислено: `{final_amount}` монет",
            parse_mode="Markdown"
        )

    # 4. Промокоды
    elif cmd == "промо":
        if len(parts) < 2:
            return await message.answer("❌ Укажите код промокода. Пример: `промо START`", parse_mode="Markdown")
        code = parts[1].upper()

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
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

    # 5. Казино текстовое меню
    elif cmd == "казино":
        return await message.answer(
            "🎰 **Игровое казино:**\n\n"
            "Доступные игры:\n"
            "• `слоты <ставка>` — сыграть в слоты (мин. 5)\n"
            "• `кости <ставка>` — бросить кости (мин. 5)\n"
            "• `мины <ставка>` — сыграть в мины (мин. 5)",
            parse_mode="Markdown"
        )

    # 6. Слоты
    elif cmd == "слоты":
        if len(parts) < 2 or not parts[1].isdigit():
            return await message.answer("❌ Формат: `слоты <ставка>`", parse_mode="Markdown")
        bet = int(parts[1])
        if bet < 5:
            return await message.answer("❌ Минимальная ставка — 5 монет.")

        bal, vip_exp, _ = get_user_data(user_id)
        if bal < bet:
            return await message.answer(f"❌ Мало монет на балансе! У вас: {bal}, а ставка: {bet}")

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
            conn.commit()

        msg = await message.answer_dice("🎰")
        await asyncio.sleep(2.5)

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            if msg.dice.value in [1, 22, 43, 64]:
                win = (bet * 5) * (2 if is_vip(vip_exp) else 1)
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, user_id))
                conn.commit()
                await message.answer(f"🎰 **ДЖЕКПОТ!** Выиграл `{win}` монет!", parse_mode="Markdown")
            else:
                await message.answer("😢 Мимо, бро. Повезет в следующий раз.")

    # 7. Кости
    elif cmd == "кости":
        if len(parts) < 2 or not parts[1].isdigit():
            return await message.answer("❌ Формат: `кости <ставка>`", parse_mode="Markdown")
        bet = int(parts[1])
        if bet < 5:
            return await message.answer("❌ Минимальная ставка — 5 монет.")

        bal, vip_exp, _ = get_user_data(user_id)
        if bal < bet:
            return await message.answer(f"❌ Мало монет на балансе! У вас: {bal}, а ставка: {bet}")

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
            conn.commit()

        msg = await message.answer_dice("🎲")
        await asyncio.sleep(3)

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            if msg.dice.value >= 4:
                win = (bet * 2) * (2 if is_vip(vip_exp) else 1)
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, user_id))
                conn.commit()
                await message.answer(f"🎯 Выпало {msg.dice.value}! Забирай выигрыш: `{win}` монет!", parse_mode="Markdown")
            else:
                await message.answer(f"😢 Выпало {msg.dice.value}. Луз.")

    # 8. Мины
    elif cmd == "мины":
        if len(parts) < 2 or not parts[1].isdigit():
            return await message.answer("❌ Формат: `мины <ставка>`", parse_mode="Markdown")
        bet = int(parts[1])
        if bet < 5:
            return await message.answer("❌ Минимальная ставка — 5 монет.")

        bal, vip_exp, _ = get_user_data(user_id)
        if bal < bet:
            return await message.answer(f"❌ Мало монет на балансе! У вас: {bal}, а ставка: {bet}")

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
            conn.commit()

        chance = 0.25 - (0.15 if is_vip(vip_exp) else 0)

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            if random.random() > chance:
                win = int(bet * 2) * (2 if is_vip(vip_exp) else 1)
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, user_id))
                conn.commit()
                await message.answer(f"💰 **Изи катка!** Поле чистое. Выигрыш: `{win}` монет!", parse_mode="Markdown")
            else:
                await message.answer("💥 **БУХ!** Нарвался на мину, луз.", parse_mode="Markdown")


# Запуск бота
async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

