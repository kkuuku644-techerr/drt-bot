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

# Инициализация бота и админа
TOKEN = "8983343344:AAFSfWIZdeqOffaycVrhU5TWC0eTA9FSpRU"
ADMIN_ID = 7959524856  # <--- ВПИШИ СЮДА СВОЙ TELEGRAM ID ЦИФРАМИ!

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
            username TEXT,
            balance INTEGER DEFAULT 100,
            vip_expires TEXT,
            last_daily TEXT,
            referrer INTEGER
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY,
            reward INTEGER,
            max_uses INTEGER,
            uses_count INTEGER DEFAULT 0
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

def get_user_data(user_id, username=None):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance, vip_expires, last_daily FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, 100)", (user_id, username))
            conn.commit()
            return 100, None, None
        else:
            if username:
                cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
                conn.commit()
        return row[0], row[1], row[2]

def find_user_by_username(username):
    username = username.lstrip("@").lower()
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE LOWER(username) = ?", (username,))
        row = cursor.fetchone()
        return row[0] if row else None

def is_vip(vip_expires):
    if not vip_expires:
        return False
    return datetime.fromisoformat(vip_expires) > datetime.now()


# --- КЛАВИАТУРЫ ---
def get_main_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(text="🎰 Казино", callback_data="menu_casino")],
        [InlineKeyboardButton(text="🛒 Магазин (Монеты / VIP)", callback_data="menu_shop")],
        [InlineKeyboardButton(text="🎁 Ежедневная Награда", callback_data="daily_reward")],
        [InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="ref_link")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="adm_create_promo")],
        [InlineKeyboardButton(text="📜 Список промокодов", callback_data="adm_list_promos")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_main")]
    ])


# --- СТАРТ ---
@router.message(Command("start"))
@router.message(F.text.lower() == "старт")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    get_user_data(user_id, username)

    if message.chat.type == "private":
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

        await message.answer("Привет! Выбери нужный раздел в меню:", reply_markup=get_main_keyboard(user_id))


# --- КОЛБЭКИ И АДМИН-ПАНЕЛЬ ---
@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text("Привет! Выбери нужный раздел в меню:", reply_markup=get_main_keyboard(callback.from_user.id))
    except:
        pass


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    bal, vip_exp, _ = get_user_data(user_id, callback.from_user.username)
    vip_status = f"💎 До {datetime.fromisoformat(vip_exp).strftime('%d.%m.%Y')}" if is_vip(vip_exp) else "Обычный"

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
        f"• **500 монет**\n"
        f"• **VIP статус (30 дней)** — удваивает выигрыши и снижает шанс луза в минах!"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_shop_keyboard(), parse_mode="Markdown")
    except:
        pass


@router.callback_query(F.data.in_({"game_slots_info", "game_dice_info", "game_mines_info"}))
async def cb_game_info(callback: CallbackQuery):
    games = {
        "game_slots_info": "слоты <ставка>",
        "game_dice_info": "кости <ставка>",
        "game_mines_info": "мины <ставка>"
    }
    await callback.answer(f"Напиши в чат команду: {games.get(callback.data)}", show_alert=True)


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Доступ запрещен!", show_alert=True)
    await callback.answer()
    text = (
        "👑 **Админ-панель управления**\n\n"
        "Вы можете выдавать монеты и VIP прямо через чат командами:\n"
        "• `/addbal <ID/@username> <сумма>` — выдать монеты\n"
        "• `/delbal <ID/@username> <сумма>` — забрать монеты\n"
        "• `/addvip <ID/@username> <дни>` — выдать VIP статус\n\n"
        "Или управлять промокодами ниже:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    except:
        pass


@router.callback_query(F.data == "adm_create_promo")
async def cb_adm_create_promo(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Доступ запрещен!", show_alert=True)
    await callback.answer()
    text = (
        "📝 **Как создать промокод:**\n"
        "Напишите в чат команду в таком формате:\n"
        "`/createpromo <КОД> <НАГРАДА> <КОЛ-ВО_АКТИВАЦИЙ>`\n\n"
        "Пример: `/createpromo BONUS 250 10`"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    except:
        pass


@router.callback_query(F.data == "adm_list_promos")
async def cb_adm_list_promos(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Доступ запрещен!", show_alert=True)

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code, reward, max_uses, uses_count FROM promos")
        promos = cursor.fetchall()

    if not promos:
        text = "📜 Активных промокодов нет."
    else:
        text = "📜 **Список промокодов:**\n\n"
        for p in promos:
            text += f"• Код: `{p[0]}` | Награда: `{p[1]}` | Активаций: `{p[3]}/{p[2]}`\n"

    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    except:
        pass


# --- ПЛАТЕЖИ ---
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
    _, _, last_daily = get_user_data(user_id, callback.from_user.username)

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


# --- АДМИНСКИЕ КОМАНДЫ (ЧЕРЕЗ СЛЕШ) ---
def parse_target(target_str):
    if target_str.isdigit():
        return int(target_str)
    elif target_str.startswith("@"):
        return find_user_by_username(target_str)
    return None

@router.message(Command("createpromo"))
async def admin_create_promo(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 4 or not parts[2].isdigit() or not parts[3].isdigit():
        return await message.answer("❌ Формат: `/createpromo <КОД> <НАГРАДА> <КОЛ-ВО>`", parse_mode="Markdown")

    code = parts[1].upper()
    reward = int(parts[2])
    max_uses = int(parts[3])

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO promos (code, reward, max_uses, uses_count) VALUES (?, ?, ?, 0)", (code, reward, max_uses))
        conn.commit()

    await message.answer(f"✅ Промокод `{code}` успешно создан!\n💰 Награда: `{reward}` монет\n👥 Активаций: `{max_uses}`", parse_mode="Markdown")


@router.message(Command("addbal"))
async def admin_add_bal(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3 or not parts[2].isdigit():
        return await message.answer("❌ Формат: `/addbal <ID/@username> <сумма>`", parse_mode="Markdown")

    target_id = parse_target(parts[1])
    amount = int(parts[2])

    if not target_id:
        return await message.answer("❌ Пользователь не найден в базе данных (он должен хотя бы раз запустить бота).")

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()

    await message.answer(f"✅ Успешно начислено `{amount}` монет пользователю `(ID: {target_id})`.", parse_mode="Markdown")


@router.message(Command("delbal"))
async def admin_del_bal(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3 or not parts[2].isdigit():
        return await message.answer("❌ Формат: `/delbal <ID/@username> <сумма>`", parse_mode="Markdown")

    target_id = parse_target(parts[1])
    amount = int(parts[2])

    if not target_id:
        return await message.answer("❌ Пользователь не найден в базе данных.")

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (amount, target_id))
        conn.commit()

    await message.answer(f"✅ Успешно списано `{amount}` монет у пользователя `(ID: {target_id})`.", parse_mode="Markdown")


@router.message(Command("addvip"))
async def admin_add_vip(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3 or not parts[2].isdigit():
        return await message.answer("❌ Формат: `/addvip <ID/@username> <дни>`", parse_mode="Markdown")

    target_id = parse_target(parts[1])
    days = int(parts[2])

    if not target_id:
        return await message.answer("❌ Пользователь не найден в базе данных.")

    _, current_vip, _ = get_user_data(target_id)
    base_date = datetime.now()
    if current_vip and datetime.fromisoformat(current_vip) > base_date:
        base_date = datetime.fromisoformat(current_vip)

    new_vip_date = (base_date + timedelta(days=days)).isoformat()

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET vip_expires = ? WHERE user_id = ?", (new_vip_date, target_id))
        conn.commit()

    await message.answer(f"💎 Пользователю `(ID: {target_id})` выдан VIP-статус на `{days}` дней!", parse_mode="Markdown")


# --- ТЕКСТОВЫЕ КОМАНДЫ И ИГРЫ ---
@router.message(F.text)
async def text_commands_router(message: Message):
    if not message.text:
        return

    user_id = message.from_user.id
    username = message.from_user.username
    get_user_data(user_id, username)

    text_lower = message.text.lower().strip()
    parts = text_lower.split()
    if not parts:
        return

    cmd = parts[0]

    # 1. Баланс
    if cmd in ("б", "баланс"):
        bal, _, _ = get_user_data(user_id, username)
        return await message.answer(f"💰 Ваш баланс: `{bal}` монет", parse_mode="Markdown")

    # 2. Паспорт
    elif cmd == "паспорт":
        bal, vip_exp, _ = get_user_data(user_id, username)
        vip_status = f"💎 До {datetime.fromisoformat(vip_exp).strftime('%d.%m.%Y')}" if is_vip(vip_exp) else "Обычный"
        text = (
            f"📜 **Паспорт игрока:**\n"
            f"👤 Имя: {message.from_user.first_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💰 Монеты: `{bal}`\n"
            f"🌟 Уровень: {vip_status}"
        )
        return await message.answer(text, parse_mode="Markdown")

    # 3. Перевод монет
    elif cmd in ("передать", "перевод", "pay"):
        target_id = None
        amount = None

        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            if len(parts) >= 2 and parts[1].isdigit():
                amount = int(parts[1])
        else:
            if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                target_id = int(parts[1])
                amount = int(parts[2])

        if not target_id or not amount:
            return await message.answer(
                "❌ **Неверный формат команды!**\n"
                "• Ответом: `перевод <сумма>`\n"
                "• По ID: `передать <айди> <сумма>`",
                parse_mode="Markdown"
            )

        if amount <= 0:
            return await message.answer("❌ Сумма перевода должна быть больше нуля.")
        if target_id == user_id:
            return await message.answer("❌ Нельзя переводить монеты самому себе!")

        bal, _, _ = get_user_data(user_id, username)
        if bal < amount:
            return await message.answer(f"❌ Недостаточно монет! Ваш баланс: `{bal}` монет.", p        bal, _, _ = get_user_data(user_id, username)
        if bal < amount:
            return await message.answer(f"❌ Недостаточно монет! Ваш баланс: `{bal}` монет.", parse_mode="Markdown")

        get_user_data(target_id)
        commission = int(amount * 0.10)
        final_amount = amount - commission

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (final_amount, target_id))
            conn.commit()

        return await message.answer(
            f"✅ Успешный перевод!\n"
            f"📤 Списано с учетом комиссии (10%): `{amount}` монет\n"
            f"📥 Получателю зачислено: `{final_amount}` монет",
            parse_mode="Markdown"
        )

    # 4. Промокоды (Работают для всех с учетом лимитов)
    elif cmd == "промо":
        if len(parts) < 2:
            return await message.answer("❌ Укажите код промокода. Пример: `промо START`", parse_mode="Markdown")
        code = parts[1].upper()

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT reward, max_uses, uses_count FROM promos WHERE code = ?", (code,))
            promo = cursor.fetchone()
            if not promo:
                return await message.answer("❌ Такого промокода не существует.")

            reward, max_uses, uses_count = promo[0], promo[1], promo[2]

            if uses_count >= max_uses:
                return await message.answer("❌ Лимит активаций этого промокода исчерпан!")

            cursor.execute("SELECT * FROM used_promos WHERE user_id = ? AND code = ?", (user_id, code))
            if cursor.fetchone():
                return await message.answer("❌ Вы уже активировали этот промокод!")

            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
            cursor.execute("UPDATE promos SET uses_count = uses_count + 1 WHERE code = ?", (code,))
            cursor.execute("INSERT INTO used_promos (user_id, code) VALUES (?, ?)", (user_id, code))
            conn.commit()

        return await message.answer(f"✅ Промокод успешно активирован! Вам зачислено: `{reward}` монет.", parse_mode="Markdown")

    # 5. Казино меню
    elif cmd == "казино":
        return await message.answer(
            "🎰 **Игровое казино:**\n\n"
            "Доступные игры:\n"
            "• `слоты <ставка>`\n"
            "• `кости <ставка>`\n"
            "• `мины <ставка>`",
            parse_mode="Markdown"
        )

    # 6. Слоты
    elif cmd == "слоты":
        if len(parts) < 2 or not parts[1].isdigit():
            return await message.answer("❌ Формат: `слоты <ставка>`", parse_mode="Markdown")
        bet = int(parts[1])
        if bet < 5:
            return await message.answer("❌ Минимальная ставка — 5 монет.")

        bal, vip_exp, _ = get_user_data(user_id, username)
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

        bal, vip_exp, _ = get_user_data(user_id, username)
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

        bal, vip_exp, _ = get_user_data(user_id, username)
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

