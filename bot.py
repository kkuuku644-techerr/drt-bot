import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
    ChatMemberUpdated
)
from aiogram.enums import ChatMemberStatus

TOKEN = "8935480244:AAHeLi0e2Aqe2RA9m2oh8v9vGkHNwSsAPPI"
CREATOR_ID = 7959524856
ADMIN_CHAT_ID = -1004410094117
CHANNEL_ID = -1004404647295  # Твой правильный ID канала для публикаций
CHANNEL_LINK = "https://t.me/+pQLlazfn-lxjOTE6"

bot = Bot(token=TOKEN)
dp = Dispatcher()

users_balance = {}
waiting_for_sliv = set()

def get_user_data(user_id: int) -> dict:
    if user_id not in users_balance:
        users_balance[user_id] = {"coins": 500, "pigs": 50, "vip_until": None}

    data = users_balance[user_id]
    if data["vip_until"] and datetime.now() > data["vip_until"]:
        data["vip_until"] = None
    return data

def is_vip(user_id: int) -> bool:
    data = get_user_data(user_id)
    return data["vip_until"] is not None

# Проверка приписок (drt, pig.zip, d1rty) в имени пользователя
def check_user_tags(user) -> str:
    full_str = f"{user.first_name or ''} {user.last_name or ''}".lower()
    tags = ["drt", "pig.zip", "d1rty"]
    for tag in tags:
        if tag in full_str:
            return "да"
    return "нет"

def check_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)]
    ])

async def check_user_subscription(user_id: int) -> bool:
    return True

# Защита групп
@dp.my_chat_member()
async def bot_added_to_chat(event: ChatMemberUpdated):
    if event.chat.type in ["group", "supergroup"]:
        if event.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
            adder_id = event.from_user.id
            if adder_id != CREATOR_ID:
                try:
                    await bot.send_message(event.chat.id, "❌ Этот бот может быть добавлен в группы только создателем.")
                    await bot.leave_chat(event.chat.id)
                except Exception:
                    pass

def get_main_reply_keyboard(user_id: int):
    buttons = [
        [KeyboardButton(text="🎰 Казино"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="⭐ Магазин (Звёзды)"), KeyboardButton(text="🔄 Обмен свиней")],
        [KeyboardButton(text="💸 Слить >_<")]
    ]
    if user_id == CREATOR_ID:
        buttons.insert(0, [KeyboardButton(text="🛠 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if message.chat.type == "private":
        text = (
            "Привет! Это бот @d1rtytgk от грязнуль!\n"
            "Выбери кнопочку ниже для услуги))"
        )
        await message.answer(text, reply_markup=get_main_reply_keyboard(user_id))
    else:
        await message.answer("🎰 Бот грязнуль в группе активен!\n• Ставка: `/bet [сумма]`\n• Паспорт: `/profile` или `паспорт`", parse_mode="Markdown")

# === ПАСПОРТ / ПРОФИЛЬ (Везде: в ЛС и в группе) ===
@dp.message(F.text.lower().in_({"/profile", "паспорт", "/паспорт"}))
async def cmd_profile_general(message: Message):
    user = message.from_user
    user_id = user.id
    username_str = f"@{user.username}" if user.username else "отсутствует"
    data = get_user_data(user_id)

    if is_vip(user_id):
        expire_date = data["vip_until"].strftime("%d.%m.%Y")
        vip_status = f"есть (до {expire_date})"
    else:
        vip_status = "нет"

    has_tag = check_user_tags(user)

    text = (
        f"ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ @{user.username or user.first_name}\n"
        f"Юзернейм: {username_str}\n"
        f"ID 🪪 : `{user_id}`\n"
        f"Баланс:\n"
        f"  Свиней: `{data['pigs']}` 🐷\n"
        f"  Монеток: `{data['coins']}` 🪙\n"
        f"VIP статус: {vip_status}\n"
        f"Имеет приписку: {has_tag} (приписки: drt, pig.zip, d1rty)"
    )
    await message.answer(text, parse_mode="Markdown")

# === СТАВКА В ГРУППЕ ИЛИ ЛС (/bet [сумма]) С УЧЕТОМ ВИП ===
@dp.message(Command("bet"))
async def cmd_bet(message: Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Укажи сумму ставки! Пример: `/bet 50`", parse_mode="Markdown")
        return

    try:
        amount = int(args[1])
    except ValueError:
        await message.answer("❌ Сумма должна быть числом!")
        return

    if amount <= 0:
        await message.answer("❌ Ставка должна быть больше нуля!")
        return

    if data["coins"] < amount:
        await message.answer(f"❌ Недостаточно монеток! У тебя: {data['coins']} 🪙")
        return

    win_chance = 0.50 if is_vip(user_id) else 0.35

    if random.random() < win_chance:
        multiplier = 1.5 if is_vip(user_id) else 1.8
        win_amount = int(amount * multiplier)
        data["coins"] += (win_amount - amount)
        vip_text = " (👑 VIP бонус x1.5)" if is_vip(user_id) else ""
        await message.answer(f"🎉 **Победа!** Выиграно `{win_amount}` монеток{vip_text}!\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    else:
        data["coins"] -= amount
        await message.answer(f"💥 **Проигрыш!** Потеряно `{amount}` монеток.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")

# Обработка кнопок меню в ЛС
@dp.message(F.text.in_({
    "🎰 Казино", "👤 Профиль", "⭐ Магазин (Звёзды)", "🔄 Обмен свиней", "💸 Слить >_<", "🛠 Админ-панель"
}))
async def handle_reply_buttons(message: Message):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    text = message.text

    if not await check_user_subscription(user_id):
        await message.answer("⚠️ Сначала подпишитесь на канал!", reply_markup=check_sub_keyboard())
        return

    if text == "🎰 Казино":
        casino_text = (
            "Привет! Добро пожаловать в официальное казино грязнуль. Выбери игру по душе.\n\n"
            "⚡️ Если что казино находится в разработке, об ошибках сообщать: @owndrt"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Бросить кости (ставка)", callback_data="game_dice")],
            [InlineKeyboardButton(text="🪙 Орёл и Решка (ставка)", callback_data="game_coin")],
            [InlineKeyboardButton(text="💣 Мины (ставка)", callback_data="game_mines")]
        ])
        await message.answer(casino_text, reply_markup=keyboard, parse_mode="Markdown")

    elif text == "👤 Профиль":
        user = message.from_user
        username_str = f"@{user.username}" if user.username else "отсутствует"
        data = get_user_data(user_id)
        if is_vip(user_id):
            vip_status = f"есть до {data['vip_until'].strftime('%d.%m.%Y')}"
        else:
            vip_status = "нет"
        has_tag = check_user_tags(user)

        prof_text = (
            f"ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ @{user.username or user.first_name}\n"
            f"Юзернейм: {username_str}\n"
            f"ID 🪪 : `{user_id}`\n"
            f"Баланс:\n"
            f"  Свиней: `{data['pigs']}` 🐷\n"
            f"  Монеток: `{data['coins']}` 🪙\n"
            f"VIP статус: {vip_status}\n"
            f"Имеет приписку: {has_tag} (приписки: drt, pig.zip, d1rty)"
        )
        await message.answer(prof_text, parse_mode="Markdown")

    elif text == "⭐ Магазин (Звёзды)":
        shop_text = (
            "Привет! Это официальный шоп грязнуль. Выбери услугу которая тебе нужна ^^\n\n"
            "Прайс:\n"
            "VIP STATUS: 25 STARS\n"
            "1000 PIGCOINS: 5 STARS\n"
            "10.000 PIGCOINS: 10 STARS\n"
            "15.000 PIGCOINS: 20 STARS\n"
            "20.000 PIGCOINS: 25 STARS"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ VIP статус (25 ⭐)", callback_data="buy_vip")],
            [InlineKeyboardButton(text="🪙 1000 монеток (5 ⭐)", callback_data="buy_coins_1000")],
            [InlineKeyboardButton(text="🪙 10.000 монеток (10 ⭐)", callback_data="buy_coins_10k")],
            [InlineKeyboardButton(text="🪙 15.000 монеток (20 ⭐)", callback_data="buy_coins_15k")],
            [InlineKeyboardButton(text="🪙 20.000 монеток (25 ⭐)", callback_data="buy_coins_20k")]
        ])
        await message.answer(shop_text, reply_markup=keyboard, parse_mode="Markdown")

    elif text == "🔄 Обмен свиней":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обменять 20 свиней ➡️ 50 монеток", callback_data="do_exchange")]
        ])
        data = get_user_data(user_id)
        await message.answer(f"🔄 **Обмен свиней**\n\nТвои свиньи: {data['pigs']} 🐷\n20 свиней = 50 монеток.", reply_markup=keyboard, parse_mode="Markdown")

    elif text == "💸 Слить >_<":
        waiting_for_sliv.add(user_id)
        sliv_text = (
            "Приветик зайкаа!! Скинь свой тейк. Админы рассмотрят и выложат его в тгк\n"
            "Самослив не делать\n"
            "Юзы только пруф+причина\n"
            "Если хотите слить ссылку просто скиньте нам ее"
        )
        await message.answer(sliv_text, parse_mode="Markdown")

    elif text == "🛠 Админ-панель" and user_id == CREATOR_ID:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 Выдать себе VIP", callback_data="adm_give_vip")],
            [InlineKeyboardButton(text="🪙 Накрутить +10,000 монеток", callback_data="adm_give_coins")],
            [InlineKeyboardButton(text="🐷 Накрутить +500 свиней", callback_data="adm_give_pigs")]
        ])
        await message.answer("🛠 **Панель Администратора**", reply_markup=keyboard, parse_mode="Markdown")

# === СЛИВЫ (Пересылка в админ-чат с кнопкой подтверждения) ===
@dp.message(F.chat.type == "private")
async def handle_user_uploads(message: Message):
    user_id = message.from_user.id
    if user_id in waiting_for_sliv:
        waiting_for_sliv.remove(user_id)

        approve_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить и выложить", callback_data=f"give_pigs_{user_id}")]
        ])

        await message.forward(chat_id=ADMIN_CHAT_ID)
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🚨 **Новый слив на проверку!**\n👤 От: {message.from_user.full_name} (@{message.from_user.username or 'нет'})\n🆔 ID: `{user_id}`",
            reply_markup=approve_keyboard,
            parse_mode="Markdown"
        )
        await message.answer("✅ Твой слив отправлен админам на проверку!")

# Подтверждение слива и автопубликация в ТГК
@dp.callback_query(F.data.startswith("give_pigs_"))
async def cb_approve_sliv(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    target_id = int(callback.data.split("_")[2])
    target_data = get_user_data(target_id)

    pigs_reward = 40 if is_vip(target_id) else 20
    target_data["pigs"] += pigs_reward

    # Публикация в ТГК
    try:
        await callback.message.copy_to(chat_id=CHANNEL_ID)
    except Exception as e:
        print(f"Ошибка публикации в ТГК: {e}")

    # Уведомление юзеру
    try:
        vip_note = " (включая х2 VIP бонус!)" if pigs_reward == 40 else ""
        await bot.send_message(target_id, f"🎉 **Слив проверен и выложен в канал!** Тебе зачислено **+{pigs_reward} свиней 🐷**{vip_note}!", parse_mode="Markdown")
    except Exception:
        pass

    await callback.message.edit_text(f"{callback.message.text}\n\n✅ **ОДОБРЕНО (Опубликовано в ТГК, начислено {pigs_reward} свиней)**", parse_mode="Markdown")
    await callback.answer("✅ Слив выложен в ТГК и свиньи начислены!", show_alert=True)

# Админ-панель кнопки
@dp.callback_query(F.data == "adm_give_vip")
async def cb_adm_give_vip(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID: return
    data = get_user_data(CREATOR_ID)
    data["vip_until"] = datetime.now() + timedelta(days=30)
    await callback.answer("👑 VIP на 1 месяц выдан тебе бесплатно!", show_alert=True)

@dp.callback_query(F.data == "adm_give_coins")
async def cb_adm_give_coins(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID: return
    get_user_data(CREATOR_ID)["coins"] += 10000
    await callback.answer("🪙 Начислено +10,000 монеток!", show_alert=True)

@dp.callback_query(F.data == "adm_give_pigs")
async def cb_adm_give_pigs(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID: return
    get_user_data(CREATOR_ID)["pigs"] += 500
    await callback.answer("🐷 Начислено +500 свиней!", show_alert=True)

# Покупка за Звёзды (Telegram Stars)
@dp.callback_query(F.data == "buy_vip")
async def cb_buy_vip(callback: CallbackQuery):
    await callback.message.answer_invoice(
        title="VIP Status",
        description="VIP на 1 месяц: +15% удачи, х1.5 монеток в казино, х2 свиней за сливы!",
        prices=[LabeledPrice(label="VIP Status", amount=25)],
        currency="XTR",
        payload="vip_status_buy"
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_coins_1000")
async def cb_buy_c1(callback: CallbackQuery):
    await callback.message.answer_invoice(title="1000 Pigcoins", description="Пакет 1000 монеток", prices=[LabeledPrice(label="1000 Pigcoins", amount=5)], currency="XTR", payload="coins_1000")
    await callback.answer()

@dp.callback_query(F.data == "buy_coins_10k")
async def cb_buy_c2(callback: CallbackQuery):
    await callback.message.answer_invoice(title="10.000 Pigcoins", description="Пакет 10.000 монеток", prices=[LabeledPrice(label="10.000 Pigcoins", amount=10)], currency="XTR", payload="coins_10k")
    await callback.answer()

@dp.callback_query(F.data == "buy_coins_15k")
async def cb_buy_c3(callback: CallbackQuery):
    await callback.message.answer_invoice(title="15.000 Pigcoins", description="Пакет 15.000 монеток", prices=[LabeledPrice(label="15.000 Pigcoins", amount=20)], currency="XTR", payload="coins_15k")
    await callback.answer()

@dp.callback_query(F.data == "buy_coins_20k")
async def cb_buy_c4(callback: CallbackQuery):
    await callback.message.answer_invoice(title="20.000 Pigcoins", description="Пакет 20.000 монеток", prices=[LabeledPrice(label="20.000 Pigcoins", amount=25)], currency="XTR", payload="coins_20k")
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment_info = message.successful_payment
    user_id = message.from_user.id
    data = get_user_data(user_id)

    payload = payment_info.invoice_payload
    if payload == "vip_status_buy":
        data["vip_until"] = datetime.now() + timedelta(days=30)
        await message.answer("🎉 Успешно! Тебе активирован **VIP статус на 1 месяц** 👑!", parse_mode="Markdown")
    elif payload == "coins_1000":
        data["coins"] += 1000
        await message.answer("🎉 Успешно! Начислено **+1000 монеток** 🪙!", parse_mode="Markdown")
    elif payload == "coins_10k":
        data["coins"] += 10000
        await message.answer("🎉 Успешно! Начислено **+10.000 монеток** 🪙!", parse_mode="Markdown")
    elif payload == "coins_15k":
        data["coins"] += 15000
        await message.answer("🎉 Успешно! Начислено **+15.000 монеток** 🪙!", parse_mode="Markdown")
    elif payload == "coins_20k":
        data["coins"] += 20000
        await message.answer("🎉 Успешно! Начислено **+20.000 монеток** 🪙!", parse_mode="Markdown")

# === КАЗИНО ИГРЫ СО СТАВКОЙ 50 МОНЕТ ===
@dp.callback_query(F.data == "game_dice")
async def cb_game_dice(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    if data["coins"] < 50:
        await callback.answer("❌ Нужно минимум 50 монеток для ставки!", show_alert=True)
        return
    data["coins"] -= 50
    await callback.message.answer("🎲 Ставка 50 монеток принята. Бросаем кости...")
    msg = await callback.bot.send_dice(chat_id=callback.message.chat.id, emoji="🎲")

    win_values = [4, 5, 6] if is_vip(user_id) else [5, 6]
    if msg.dice.value in win_values:
        reward = 120 if is_vip(user_id) else 100
        data["coins"] += reward
        await callback.message.answer(f"🎉 Выпало {msg.dice.value}! Ты выиграл `{reward}` монеток!\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    else:
        await callback.message.answer(f"💥 Выпало {msg.dice.value}. Ставка сгорела.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "game_coin")
async def cb_game_coin(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    if data["coins"] < 50:
        await callback.answer("❌ Нужно минимум 50 монеток!", show_alert=True)
        return
    data["coins"] -= 50

    win_chance = 0.50 if is_vip(user_id) else 0.35
    if random.random() < win_chance:
        reward = int(90 * (1.5 if is_vip(user_id) else 1.0))
        data["coins"] += reward
        await callback.message.answer(f"🪙 Орёл и решка: **Победа!** Выигрыш `{reward}` монеток.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    else:
        await callback.message.answer(f"🪙 Орёл и решка: **Проигрыш!** Ставка 50 монеток сгорела.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "game_mines")
async def cb_game_mines(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    if data["coins"] < 50:
        await callback.answer("❌ Нужно минимум 50 монеток для ставки!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣", callback_data="mine_1"),
         InlineKeyboardButton(text="2️⃣", callback_data="mine_2"),
         InlineKeyboardButton(text="3️⃣", callback_data="mine_3")]
    ])
    await callback.message.answer("💣 **Мины (Ставка: 50 монеток)**\nВыбирай ячейку:", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("mine_"))
async def cb_mine_choice(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)

    if data["coins"] < 50:
        await callback.answer("❌ Недостаточно монеток!", show_alert=True)
        return

    data["coins"] -= 50

    safe_cell = str(random.randint(1, 3))
    chosen_cell = callback.data.split("_")[1]

    is_win = (chosen_cell == safe_cell) or (is_vip(user_id) and random.random() < 0.15)

    if is_win:
        reward = int(150 * (1.5 if is_vip(user_id) else 1.0))
        data["coins"] += reward
        await callback.message.edit_text(f"🎉 **Кристалл найден!** Выигрыш `{reward}` монеток.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    else:
        await callback.message.edit_text(f"💥 **БУУУМ!** Мина! Ставка 50 монеток сгорела.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "do_exchange")
async def cb_do_exchange(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    if data["pigs"] >= 20:
        data["pigs"] -= 20
        data["coins"] += 50
        await callback.answer("✅ Успешно! Обменяно 20 свиней на 50 монеток.", show_alert=True)
        await callback.message.edit_text(f"🔄 Обмен свиней\n\nТвои свиньи: {data['pigs']} 🐷\nТвои монетки: {data['coins']} 🪙", parse_mode="Markdown")
    else:
        await callback.answer("❌ У тебя меньше 20 свиней!", show_alert=True)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))