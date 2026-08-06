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
CHANNEL_LINK = "https://t.me/+pQLlazfn-lxjOTE6"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Балансы и статусы: {"coins": 500, "pigs": 50, "vip_until": datetime или None}
users_balance = {}
waiting_for_sliv = set()

def get_user_data(user_id: int) -> dict:
    if user_id not in users_balance:
        users_balance[user_id] = {"coins": 500, "pigs": 50, "vip_until": None}

    # Проверка на истечение срока VIP (1 месяц)
    data = users_balance[user_id]
    if data["vip_until"] and datetime.now() > data["vip_until"]:
        data["vip_until"] = None  # Срок вышел
    return data

def is_vip(user_id: int) -> bool:
    data = get_user_data(user_id)
    return data["vip_until"] is not None

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
        await message.answer("👋 Привет! Используй меню внизу или пиши /profile (паспорт).", reply_markup=get_main_reply_keyboard(user_id))
    else:
        await message.answer("🎰 Бот в группе активен!\n• Ставка: `/bet [сумма]`\n• Паспорт: `/profile` или `паспорт`", parse_mode="Markdown")

# === ПАСПОРТ / ПРОФИЛЬ (Везде: и в ЛС, и в группе) ===
@dp.message(F.text.lower().in_({"/profile", "паспорт", "/паспорт"}))
async def cmd_profile_general(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    data = get_user_data(user_id)

    if is_vip(user_id):
        expire_date = data["vip_until"].strftime("%d.%m.%Y")
        vip_status = f"👑 VIP Активен (до {expire_date})"
    else:
        vip_status = "❌ Нет"

    text = (
        f"📄 **Паспорт игрока {user_name}**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"🪙 Монеты: `{data['coins']}`\n"
        f"🐷 Свиньи: `{data['pigs']}`\n"
        f"⭐ VIP статус: {vip_status}"
    )
    await message.answer(text, parse_mode="Markdown")

# === СТАВКА В ГРУППЕ ИЛИ ЛС (/bet [сумма]) С УЧЕТОМ ВИП (+15% удачи, x1.5 монет) ===
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
        await message.answer(f"❌ Недостаточно монет! У тебя: {data['coins']} 🪙")
        return

    # Базовый шанс 35%, для VIP +15% (итого 50%)
    win_chance = 0.50 if is_vip(user_id) else 0.35

    if random.random() < win_chance:
        # Для VIP множитель выигрыша x1.5, для обычных x1.8 от чистой ставки или стандартный
        multiplier = 1.5 if is_vip(user_id) else 1.8
        win_amount = int(amount * multiplier)
        data["coins"] += (win_amount - amount)
        vip_text = " (👑 VIP бонус x1.5)" if is_vip(user_id) else ""
        await message.answer(f"🎉 **Победа!** Выиграно `{win_amount}` монет{vip_text}!\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    else:
        data["coins"] -= amount
        await message.answer(f"💥 **Проигрыш!** Потеряно `{amount}` монет.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")

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
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Бросить кости (ставка)", callback_data="game_dice")],
            [InlineKeyboardButton(text="🪙 Орёл и Решка (ставка)", callback_data="game_coin")],
            [InlineKeyboardButton(text="💣 Мины (ставка)", callback_data="game_mines")]
        ])
        await message.answer("🎰 **Казино**\nВсе игры идут на монеты со ставкой в 50 монет:", reply_markup=keyboard, parse_mode="Markdown")

    elif text == "👤 Профиль":
        data = get_user_data(user_id)
        vip_status = f"👑 VIP (до {data['vip_until'].strftime('%d.%m.%Y')})" if is_vip(user_id) else "❌ Нет"
        await message.answer(f"👤 **Твой профиль**\n\n🆔 ID: `{user_id}`\n🪙 Монеты: `{data['coins']}`\n🐷 Свиньи: `{data['pigs']}`\n⭐ VIP: {vip_status}", parse_mode="Markdown")

    elif text == "⭐ Магазин (Звёзды)":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ VIP на 1 месяц (25 ⭐)", callback_data="buy_vip")],
            [InlineKeyboardButton(text="🪙 500 монет (15 ⭐)", callback_data="buy_coins_1")]
        ])
        await message.answer("⭐ **Магазин за Telegram Звёзды**", reply_markup=keyboard, parse_mode="Markdown")

    elif text == "🔄 Обмен свиней":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обменять 20 свиней ➡️ 50 монет", callback_data="do_exchange")]
        ])
        data = get_user_data(user_id)
        await message.answer(f"🔄 **Обмен свиней**\n\nТвои свиньи: {data['pigs']} 🐷\n20 свиней = 50 монет.", reply_markup=keyboard, parse_mode="Markdown")

    elif text == "💸 Слить >_<":
        waiting_for_sliv.add(user_id)
        await message.answer("💸 **Отправь материалы для слива** (фото, видео, файл) в этот чат.\nАдмин проверит их, и тебе начислится награда!", parse_mode="Markdown")

    elif text == "🛠 Админ-панель" and user_id == CREATOR_ID:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 Выдать себе VIP", callback_data="adm_give_vip")],
            [InlineKeyboardButton(text="🪙 Накрутить +10,000 монет", callback_data="adm_give_coins")],
            [InlineKeyboardButton(text="🐷 Накрутить +500 свиней", callback_data="adm_give_pigs")]
        ])
        await message.answer("🛠 **Панель Администратора**", reply_markup=keyboard, parse_mode="Markdown")

# === ИСПРАВЛЕННЫЕ СЛИВЫ (Пересылка в админ-чат с кнопкой) ===
@dp.message(F.chat.type == "private")
async def handle_user_uploads(message: Message):
    user_id = message.from_user.id
    if user_id in waiting_for_sliv:
        waiting_for_sliv.remove(user_id)

        approve_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить слив", callback_data=f"give_pigs_{user_id}")]
        ])

        await message.forward(chat_id=ADMIN_CHAT_ID)
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🚨 **Новый слив!**\n👤 От: {message.from_user.full_name}\n🆔 ID: `{user_id}`",
            reply_markup=approve_keyboard,
            parse_mode="Markdown"
        )
        await message.answer("✅ Материал отправлен админу на проверку!")

@dp.callback_query(F.data.startswith("give_pigs_"))
async def cb_approve_sliv(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    target_id = int(callback.data.split("_")[2])
    target_data = get_user_data(target_id)

    # VIP бонус: у VIP х2 свиней за сливы (40 вместо 20)
    pigs_reward = 40 if is_vip(target_id) else 20
    target_data["pigs"] += pigs_reward

    try:
        vip_note = " (включая х2 VIP бонус!)" if pigs_reward == 40 else ""
        await bot.send_message(target_id, f"🎉 **Слив подтвержден!** Начислено **+{pigs_reward} свиней 🐷**{vip_note}!", parse_mode="Markdown")
    except Exception:
        pass

    await callback.message.edit_text(f"{callback.message.text}\n\n✅ **ОДОБРЕНО (Начислено {pigs_reward} свиней)**", parse_mode="Markdown")
    await callback.answer("✅ Слив зачтен!", show_alert=True)

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
    await callback.answer("🪙 Начислено +10,000 монет!", show_alert=True)

@dp.callback_query(F.data == "adm_give_pigs")
async def cb_adm_give_pigs(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID: return
    get_user_data(CREATOR_ID)["pigs"] += 500
    await callback.answer("🐷 Начислено +500 свиней!", show_alert=True)

# Звёзды магазин
@dp.callback_query(F.data == "buy_vip")
async def cb_buy_vip(callback: CallbackQuery):
    await callback.message.answer_invoice(
        title="VIP Статус (1 месяц)",
        description="+15% удачи в казино, х1.5 монет, х2 свиней за сливы!",
        prices=[LabeledPrice(label="VIP на месяц", amount=25)],
        currency="XTR",
        payload="vip_status_buy"
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_coins_1")
async def cb_buy_coins(callback: CallbackQuery):
    await callback.message.answer_invoice(
        title="Пакет монет (500 шт.)",
        description="Покупка 500 монет для казино.",
        prices=[LabeledPrice(label="500 монет", amount=15)],
        currency="XTR",
        payload="coins_500_buy"
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment_info = message.successful_payment
    user_id = message.from_user.id
    data = get_user_data(user_id)
    if payment_info.invoice_payload == "vip_status_buy":
        data["vip_until"] = datetime.now() + timedelta(days=30)
        await message.answer("🎉 Успешно! Тебе активирован **VIP статус на 1 месяц** 👑!", parse_mode="Markdown")
    elif payment_info.invoice_payload == "coins_500_buy":
        data["coins"] += 500
        await message.answer("🎉 Успешно! Начислено **+500 монет** 🪙!", parse_mode="Markdown")

# === КАЗИНО ИГРЫ В ЛС (ТОЛЬКО СО СТАВКОЙ 50 МОНЕТ) ===
@dp.callback_query(F.data == "game_dice")
async def cb_game_dice(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    if data["coins"] < 50:
        await callback.answer("❌ Нужно минимум 50 монет для ставки!", show_alert=True)
        return
    data["coins"] -= 50
    await callback.message.answer("🎲 Ставка 50 монет принята. Бросаем кости...")
    msg = await callback.bot.send_dice(chat_id=callback.message.chat.id, emoji="🎲")

    # Шанс победы: если VIP, то выигрывают кубики 4, 5, 6 (50%), иначе только 5, 6 (33%)
    win_values = [4, 5, 6] if is_vip(user_id) else [5, 6]
    if msg.dice.value in win_values:
        reward = 120 if is_vip(user_id) else 100
        data["coins"] += reward
        await callback.message.answer(f"🎉 Выпало {msg.dice.value}! Ты выиграл `{reward}` монет!\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    else:
        await callback.message.answer(f"💥 Выпало {msg.dice.value}. Ставка сгорела.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "game_coin")
async def cb_game_coin(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    if data["coins"] < 50:
        await callback.answer("❌ Нужно минимум 50 монет!", show_alert=True)
        return
    data["coins"] -= 50

    win_chance = 0.50 if is_vip(user_id) else 0.35
    if random.random() < win_chance:
        reward = int(90 * (1.5 if is_vip(user_id) else 1.0))
        data["coins"] += reward
        await callback.message.answer(f"🪙 Орёл и решка: **Победа!** Выигрыш `{reward}` монет.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    else:
        await callback.message.answer(f"🪙 Орёл и решка: **Проигрыш!** Ставка 50 монет сгорела.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "game_mines")
async def cb_game_mines(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    if data["coins"] < 50:
        await callback.answer("❌ Нужно минимум 50 монет для ставки!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣", callback_data="mine_1"),
         InlineKeyboardButton(text="2️⃣", callback_data="mine_2"),
         InlineKeyboardButton(text="3️⃣", callback_data="mine_3")]
    ])
    await callback.message.answer("💣 **Мины (Ставка: 50 монет)**\nВыбирай ячейку:", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("mine_"))
async def cb_mine_choice(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)

    if data["coins"] < 50:
        await callback.answer("❌ Недостаточно монет!", show_alert=True)
        return

    data["coins"] -= 50  # Списываем ставку

    # Для VIP шанс угадать выше (благоприятная ячейка определяется с учетом бонуса)
    safe_cell = str(random.randint(1, 3))
    chosen_cell = callback.data.split("_")[1]

    is_win = (chosen_cell == safe_cell) or (is_vip(user_id) and random.random() < 0.15)

    if is_win:
        reward = int(150 * (1.5 if is_vip(user_id) else 1.0))
        data["coins"] += reward
        await callback.message.edit_text(f"🎉 **Кристалл найден!** Выигрыш `{reward}` монет.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    else:
        await callback.message.edit_text(f"💥 **БУУУМ!** Мина! Ставка 50 монет сгорела.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "do_exchange")
async def cb_do_exchange(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    if data["pigs"] >= 20:
        data["pigs"] -= 20
        data["coins"] += 50
        await callback.answer("✅ Успешно! Обменяно 20 свиней на 50 монет.", show_alert=True)
        await callback.message.edit_text(f"🔄 **Обмен свиней**\n\nТвои свиньи: {data['pigs']} 🐷\nТвои монеты: {data['coins']} 🪙", parse_mode="Markdown")
    else:
        await callback.answer("❌ У тебя меньше 20 свиней!", show_alert=True)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))

