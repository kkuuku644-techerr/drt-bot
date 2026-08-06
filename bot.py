import asyncio
import random
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

users_balance = {}
bot_settings = {
    "exchange_rate": 100, 
    "welcome_text": "👋 Привет! Используй меню внизу в ЛС или играй в группе через /bet [сумма]."
}

def get_user_data(user_id: int) -> dict:
    if user_id not in users_balance:
        users_balance[user_id] = {"coins": 500, "pigs": 50, "vip": False}
    return users_balance[user_id]

def check_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)]
    ])

async def check_user_subscription(user_id: int) -> bool:
    return True

# ЗАЩИТА ГРУПП: Бот выходит из группы, если его добавил не создатель
@dp.my_chat_member()
async def bot_added_to_chat(event: ChatMemberUpdated):
    if event.chat.type in ["group", "supergroup"]:
        if event.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
            adder_id = event.from_user.id
            if adder_id != CREATOR_ID:
                try:
                    await bot.send_message(
                        event.chat.id, 
                        "❌ **Ошибка доступа!** Этот бот может быть добавлен в группы только его создателем."
                    )
                    await bot.leave_chat(event.chat.id)
                except Exception:
                    pass

# Клавиатура в ЛС
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
        await message.answer(bot_settings["welcome_text"], reply_markup=get_main_reply_keyboard(user_id))
    else:
        await message.answer("🎰 Казино-бот активирован в группе! Сделай ставку: `/bet [сумма]`", parse_mode="Markdown")

# === ИГРА В ГРУППЕ ЧЕРЕЗ /bet (Пониженный шанс победы — 35%) ===
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
        await message.answer(f"❌ Недостаточно монет! У тебя на балансе: {data['coins']} 🪙")
        return

    # Шанс победы всего 35% (настоящее казино с риском)
    if random.random() < 0.35:
        win_amount = int(amount * 1.8)
        data["coins"] += (win_amount - amount)
        await message.answer(f"🎉 **Победа в группе!** Ты выиграл `{win_amount}` монет!\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")
    else:
        data["coins"] -= amount
        await message.answer(f"💥 **Проигрыш!** Ты потерял ставку в `{amount}` монет.\n🪙 Баланс: `{data['coins']}`", parse_mode="Markdown")

# Обработка кнопок в ЛС
@dp.message(F.text.in_({
    "🎰 Казино", 
    "👤 Профиль", 
    "⭐ Магазин (Звёзды)", 
    "🔄 Обмен свиней", 
    "💸 Слить >_<", 
    "🛠 Админ-панель"
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
            [InlineKeyboardButton(text="🎲 Бросить кости", callback_data="game_dice")],
            [InlineKeyboardButton(text="🪙 Орёл и Решка", callback_data="game_coin")],
            [InlineKeyboardButton(text="💣 Мины (Сложный режим)", callback_data="game_mines")]
        ])
        await message.answer("🎰 Выбирай игру в казино:", reply_markup=keyboard)

    elif text == "👤 Профиль":
        data = get_user_data(user_id)
        vip_status = "👑 VIP Активен" if data["vip"] else "❌ Нет"
        await message.answer(
            f"👤 **Твой профиль**\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"🪙 Монеты: `{data['coins']}`\n"
            f"🐷 Свиньи: `{data['pigs']}`\n"
            f"⭐ VIP статус: {vip_status}", 
            parse_mode="Markdown"
        )

    elif text == "⭐ Магазин (Звёзды)":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Купить VIP статус (25 ⭐)", callback_data="buy_vip")],
            [InlineKeyboardButton(text="🪙 Купить 500 монет (15 ⭐)", callback_data="buy_coins_1")]
        ])
        await message.answer("⭐ **Магазин за Telegram Звёзды**\n\nВыбери товар:", reply_markup=keyboard, parse_mode="Markdown")

    elif text == "🔄 Обмен свиней":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обменять 20 свиней ➡️ 50 монет", callback_data="do_exchange")]
        ])
        data = get_user_data(user_id)
        await message.answer(
            f"🔄 **Обмен свиней**\n\nТвои свиньи: {data['pigs']} 🐷\n20 свиней = 50 монет.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    elif text == "💸 Слить >_<":
        await message.answer("💸 Отправь материалы для слива. После проверки админом ты получишь +20 свиней 🐷.")

    elif text == "🛠 Админ-панель" and user_id == CREATOR_ID:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 Выдать себе VIP", callback_data="adm_give_vip")],
            [InlineKeyboardButton(text="🪙 Накрутить +10,000 монет", callback_data="adm_give_coins")],
            [InlineKeyboardButton(text="🐷 Накрутить +500 свиней", callback_data="adm_give_pigs")]
        ])
        await message.answer("🛠 **Панель Администратора**:", reply_markup=keyboard, parse_mode="Markdown")

# Админ-кнопки
@dp.callback_query(F.data == "adm_give_vip")
async def cb_adm_give_vip(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        return
    data = get_user_data(CREATOR_ID)
    data["vip"] = True
    await callback.answer("👑 VIP-статус выдан бесплатно!", show_alert=True)

@dp.callback_query(F.data == "adm_give_coins")
async def cb_adm_give_coins(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        return
    data = get_user_data(CREATOR_ID)
    data["coins"] += 10000
    await callback.answer("🪙 Начислено +10,000 монет!", show_alert=True)

@dp.callback_query(F.data == "adm_give_pigs")
async def cb_adm_give_pigs(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        return
    data = get_user_data(CREATOR_ID)
    data["pigs"] += 500
    await callback.answer("🐷 Начислено +500 свиней!", show_alert=True)

# Звёзды
@dp.callback_query(F.data == "buy_vip")
async def cb_buy_vip(callback: CallbackQuery):
    await callback.message.answer_invoice(
        title="VIP Статус",
        description="Даёт уникальные привилегии навсегда!",
        prices=[LabeledPrice(label="VIP Статус", amount=25)],
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
        data["vip"] = True
        await message.answer("🎉 Поздравляем! Ты успешно купил **VIP статус** за 25 ⭐!", parse_mode="Markdown")
    elif payment_info.invoice_payload == "coins_500_buy":
        data["coins"] += 500
        await message.answer("🎉 Успешно! Тебе начислено **+500 монет** 🪙!", parse_mode="Markdown")

# Игры казино в ЛС
@dp.callback_query(F.data == "game_dice")
async def cb_game_dice(callback: CallbackQuery):
    await callback.message.answer("🎲 Бросаем кости...")
    await callback.bot.send_dice(chat_id=callback.message.chat.id, emoji="🎲")
    await callback.answer()

@dp.callback_query(F.data == "game_coin")
async def cb_game_coin(callback: CallbackQuery):
    result = "Орёл 🦅" if random.random() < 0.35 else "Решка 🪙"
    await callback.message.answer(f"🪙 Монетка подброшена... Выпало: **{result}**!", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "game_mines")
async def cb_game_mines(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data="mine_1"),
            InlineKeyboardButton(text="2️⃣", callback_data="mine_2"),
            InlineKeyboardButton(text="3️⃣", callback_data="mine_3")
        ]
    ])
    await callback.message.answer("💣 **Мины (Сложный режим)**\n\nСтавка: 50 монет. 2 мины и 1 кристалл (шанс победы 33%):", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("mine_"))
async def cb_mine_choice(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)

    if data["coins"] < 50:
        await callback.answer("❌ Недостаточно монет (нужно 50)!", show_alert=True)
        return

    safe_cell = str(random.randint(1, 3))
    chosen_cell = callback.data.split("_")[1]

    if chosen_cell == safe_cell:
        data["coins"] += 150
        await callback.message.edit_text(f"🎉 **Невероятно!** Кристалл найден (+150 монет).\n🪙 Твои монеты: {data['coins']}", parse_mode="Markdown")
    else:
        data["coins"] -= 50
        await callback.message.edit_text(f"💥 **БУУУМ!** Ты подорвался на мине. (-50 монет).\n🪙 Твои монеты: {data['coins']}", parse_mode="Markdown")
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

# Подтверждение слива админом
@dp.message(Command("addpigs"))
async def cmd_addpigs(message: Message):
    user_id = message.from_user.id
    if user_id != CREATOR_ID:
        return

    try:
        parts = message.text.split()
        target_id = int(parts[1])
        target_data = get_user_data(target_id)
        target_data["pigs"] += 20
        await message.answer(f"✅ Успешно! Пользователю `{target_id}` начислено +20 свиней 🐷.", parse_mode="Markdown")
        await bot.send_message(target_id, "🎉 Твой слив подтвержден! Тебе начислено **+20 свиней** 🐷!", parse_mode="Markdown")
    except Exception:
        await message.answer("❌ Ошибка! Пример: `/addpigs 7959524856`", parse_mode="Markdown")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))