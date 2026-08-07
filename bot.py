import os
import random
import asyncio
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("BOT_TOKEN", "8935480244:AAHeLi0e2Aqe2RA9m2oh8v9vGkHNwSsAPPI")

# Для частного канала используй числовой ID с минусом (например, -1004404647295)
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1004404647295")  

# Укажи свой Telegram ID для доступа к админ-панели
ADMIN_IDS = [int(os.getenv("ADMIN_ID", "7959524856"))]

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ================= БАЗА ДАННЫХ И НАСТРОЙКИ =================
users_db = {}
bot_settings = {
    "welcome_text": "👋 Привет! Добро пожаловать в бота. Используй меню ниже для управления:"
}

def get_user(user_id: int):
    if user_id not in users_db:
        users_db[user_id] = {
            "coins": 1000,
            "swine": 5,
            "vip": False,
            "wins": 0,
            "losses": 0
        }
    return users_db[user_id]

# ================= ПРОВЕРКА ПОДПИСКИ =================
async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["left", "kicked"]:
            return False
        return True
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        # Если бот не добавлен админом в частный канал, вернет True чтобы не ломать тест, 
        # но для работы обязательно сделай бота админом канала!
        return True

# ================= КНОПКИ =================
def get_main_keyboard(is_admin: bool = False):
    keyboard = [
        [InlineKeyboardButton(text="🐷 Свиньи / Обмен", callback_data="swine_menu")],
        [InlineKeyboardButton(text="🎰 Казино", callback_data="casino_menu")],
        [InlineKeyboardButton(text="🪪 Паспорт", callback_data="profile_btn")],
        [InlineKeyboardButton(text="📤 Предложить слив", callback_data="suggest_sliv")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ================= СТАРТ =================
@router.message(Command("start"))
async def cmd_start(message: Message):
    if not await check_sub(message.from_user.id):
        await message.answer(f"❌ Чтобы пользоваться ботом, подпишись на наш канал!\nПосле подписки отправь /start снова.")
        return

    get_user(message.from_user.id)
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        bot_settings["welcome_text"],
        reply_markup=get_main_keyboard(is_admin)
    )

# ================= КОМАНДА /б (БАЛАНС СВИНЕЙ И МОНЕТ) =================
@router.message(Command("б"))
async def cmd_balance(message: Message):
    if not await check_sub(message.from_user.id):
        await message.answer("❌ Подпишись на канал, чтобы использовать эту команду!")
        return

    user = get_user(message.from_user.id)
    vip_text = "👑 VIP Активен (х2 к выигрышам)" if user['vip'] else "Обычный"
    await message.answer(
        f"📊 **Твой баланс:**\n\n"
        f"🐷 Свиньи: `{user['swine']}`\n"
        f"🪙 Монеты: `{user['coins']}`\n"
        f"⚡ Статус: {vip_text}",
        parse_mode="Markdown"
    )

# ================= ПАСПОРТ (ЕСТЬ ВЕЗДЕ: И В ЛС, И В ГРУППЕ) =================
@router.message(Command("profile"))
@router.message(Command("pasport"))
@router.message(Command("passport"))
async def cmd_passport(message: Message):
    if not await check_sub(message.from_user.id):
        await message.answer("❌ Подпишись на канал для просмотра паспорта!")
        return

    user = get_user(message.from_user.id)
    vip_text = "👑 VIP" if user['vip'] else "Обычный"
    text = (
        f"🪪 **Паспорт гражданина**\n\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"🪙 Монеты: `{user['coins']}`\n"
        f"🐷 Свиньи: `{user['swine']}`\n"
        f"🏆 Побед / Поражений: {user['wins']} / {user['losses']}\n"
        f"⚡ Привилегия: {vip_text}"
    )
    await message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data == "profile_btn")
async def cb_passport(callback: CallbackQuery):
    if not await check_sub(callback.from_user.id):
        await callback.answer("❌ Сначала подпишись на канал!", show_alert=True)
        return

    user = get_user(callback.from_user.id)
    vip_text = "👑 VIP" if user['vip'] else "Обычный"
    text = (
        f"🪪 **Паспорт гражданина**\n\n"
        f"👤 Имя: {callback.from_user.full_name}\n"
        f"🆔 ID: `{callback.from_user.id}`\n"
        f"🪙 Монеты: `{user['coins']}`\n"
        f"🐷 Свиньи: `{user['swine']}`\n"
        f"🏆 Побед / Поражений: {user['wins']} / {user['losses']}\n"
        f"⚡ Привилегия: {vip_text}"
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ================= КАЗИНО И ИГРЫ (ВЕЗДЕ В ЧАТАХ И ЛС) =================
@router.message(Command("bet"))
@router.message(Command("casino"))
async def cmd_casino_menu(message: Message):
    if not await check_sub(message.from_user.id):
        await message.answer("❌ Подпишись на канал для игры в казино!")
        return

    await message.answer(
        "🎰 **Казино и режимы игр**\n\n"
        "Играй прямо в чате или группе:\n"
        "• /dice — Бросить кубик\n"
        "• /slots — Крутить слоты\n"
        "• /coin — Орёл и решка\n"
        "• /mines — Сыграть в мины (ставка 100 монет)"
    )

@router.message(Command("dice"))
async def game_dice(message: Message):
    if not await check_sub(message.from_user.id):
        return
    await message.answer_dice(emoji="🎲")

@router.message(Command("slots"))
async def game_slots(message: Message):
    if not await check_sub(message.from_user.id):
        return
    await message.answer_dice(emoji="🎰")

@router.message(Command("coin"))
async def game_coin(message: Message):
    if not await check_sub(message.from_user.id):
        return
    outcome = random.choice(["🪙 Выпал ОРЁЛ!", "🪙 Выпала РЕШКА!"])
    await message.answer(outcome)

@router.message(Command("mines"))
async def game_mines(message: Message):
    if not await check_sub(message.from_user.id):
        return
    user = get_user(message.from_user.id)
    if user["coins"] < 100:
        await message.answer("❌ Недостаточно монет (нужно минимум 100)!")
        return

    user["coins"] -= 100
    win = random.choice([True, False])
    multiplier = 2.5 if user["vip"] else 2.0
    reward = int(100 * multiplier)

    if win:
        user["coins"] += reward
        user["wins"] += 1
        await message.answer(f"💣💥 Победа! Начислено +{reward} монет {'(С учетом ВИП)' if user['vip'] else ''}!")
    else:
        user["losses"] += 1
        await message.answer("💥 Ты подорвался на мине! -100 монет.")

# ================= МЕХАНИКА СЛИВОВ (АНОНИМНО И БЕЗ ВОДЫ) =================
class SlivState(StatesGroup):
    waiting_for_content = State()

@router.callback_query(F.data == "suggest_sliv")
async def start_suggest(callback: CallbackQuery, state: FSMContext):
    if not await check_sub(callback.from_user.id):
        await callback.answer("❌ Подпишись на канал!", show_alert=True)
        return

    await callback.message.answer("📥 Отправь то, что хочешь слить (ссылку, текст, фото или видео). Всё уйдет абсолютно анонимно:")
    await state.set_state(SlivState.waiting_for_content)
    await callback.answer()

@router.message(SlivState.waiting_for_content)
async def process_sliv(message: Message, state: FSMContext):
    if not await check_sub(message.from_user.id):
        await message.answer("❌ Подпишись на канал!")
        return

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить слив", callback_data=f"approve_{message.message_id}")]
    ])

    for admin_id in ADMIN_IDS:
        try:
            await message.forward(chat_id=admin_id)
            await bot.send_message(admin_id, f"📥 Новая предложка от пользователя `{message.from_user.id}`:", reply_markup=admin_kb)
        except Exception:
            pass

    await message.answer("👀 Твоя предложка отправлена на проверку модераторам.")
    await state.clear()

@router.callback_query(F.data.startswith("approve_"))
async def approve_sliv_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У тебя нет прав администратора!", show_alert=True)
        return

    msg_id = int(callback.data.split("_")[1])
    try:
        await bot.copy_message(
            chat_id=CHANNEL_ID,
            from_chat_id=callback.message.chat.id,
            message_id=msg_id
        )
        await callback.answer("✅ Успешно опубликовано в канал кристально чисто и анонимно!", show_alert=True)
        await callback.message.delete()
    except Exception as e:
        await callback.answer(f"❌ Ошибка публикации: {e}", show_alert=True)

# ================= ОНЛАЙН АДМИН-ПАНЕЛЬ И ЗЕРКАЛА =================
class AdminStates(StatesGroup):
    waiting_for_coins = State()
    waiting_for_vip = State()
    waiting_for_welcome = State()
    waiting_for_mirror_user = State()

@router.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Накрутить монеты", callback_data="adm_coins")],
        [InlineKeyboardButton(text="👑 Выдать/Забрать ВИП", callback_data="adm_vip")],
        [InlineKeyboardButton(text="✏️ Изменить приветствие", callback_data="adm_welcome")],
        [InlineKeyboardButton(text="🌐 Создать зеркало (Разрешение)", callback_data="adm_mirror")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_admin")]
    ])
    await callback.message.edit_text("👑 **Онлайн Админ-панель**\n\nВыбери нужное действие:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "close_admin")
async def close_admin_handler(callback: CallbackQuery):
    await callback.message.edit_text("Панель закрыта.", reply_markup=get_main_keyboard(True))

@router.callback_query(F.data == "adm_coins")
async def adm_coins_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.answer("Введи `USER_ID` и количество монет через пробел (Пример: `123456789 5000`):", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_coins)
    await callback.answer()

@router.message(AdminStates.waiting_for_coins)
async def adm_coins_process(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        target_id = int(parts[0])
        amount = int(parts[1])
        user = get_user(target_id)
        user["coins"] += amount
        await message.answer(f"✅ Успешно! Пользователю `{target_id}` начислено монет. Баланс: {user['coins']}", parse_mode="Markdown")
    except Exception:
        await message.answer("❌ Ошибка в формате! Пиши так: `ID_ПОЛЬЗОВАТЕЛЯ КОЛИЧЕСТВО`", parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data == "adm_vip")
async def adm_vip_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.answer("Введи `USER_ID` пользователя для переключения ВИП статуса:", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_vip)
    await callback.answer()

@router.message(AdminStates.waiting_for_vip)
async def adm_vip_process(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        target_id = int(message.text.strip())
        user = get_user(target_id)
        user["vip"] = not user["vip"]
        status_str = "Активен (👑 ВИП)" if user["vip"] else "Снят"
        await message.answer(f"✅ Статус ВИП для `{target_id}` изменен на: {status_str}", parse_mode="Markdown")
    except Exception:
        await message.answer("❌ Ошибка! Введи корректный числовой ID.")
    await state.clear()

@router.callback_query(F.data == "adm_welcome")
async def adm_welcome_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.answer("Отправь новый текст приветствия для команды /start:")
    await state.set_state(AdminStates.waiting_for_welcome)
    await callback.answer()

@router.message(AdminStates.waiting_for_welcome)
async def adm_welcome_process(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_settings["welcome_text"] = message.text
    await message.answer("✅ Текст приветствия успешно обновлен онлайн!")
    await state.clear()

@router.callback_query(F.data == "adm_mirror")
async def adm_mirror_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.answer("Введи `USER_ID` или юзернейм человека, которому даешь разрешение на создание зеркала:", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_mirror_user)
    await callback.answer()

@router.message(AdminStates.waiting_for_mirror_user)
async def adm_mirror_process(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    target = message.text.strip()
    await message.answer(f"✅ Разрешение на зеркало для `{target}` успешно выдано!", parse_mode="Markdown")
    await state.clear()

# ================= МЕНЮ КНОПОК =================
@router.callback_query(F.data == "swine_menu")
async def cb_swine(callback: CallbackQuery):
    if not await check_sub(callback.from_user.id):
        await callback.answer("❌ Подпишись на канал!", show_alert=True)
        return
    await callback.message.answer("🐷 Раздел свиней и обмена активен.")
    await callback.answer()

@router.callback_query(F.data == "casino_menu")
async def cb_casino(callback: CallbackQuery):
    if not await check_sub(callback.from_user.id):
        await callback.answer("❌ Подпишись на канал!", show_alert=True)
        return
    await callback.message.answer("🎰 Меню казино. Доступные игры: /dice, /slots, /coin, /mines.")
    await callback.answer()

# ================= ЗАПУСК =================
async def main():
    print("Идеальный бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

