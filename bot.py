import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

# ТВОИ ДАННЫЕ
TOKEN = "8981643006:AAFoHeKbNAuUuQdgMwYq2_7jUSi5JVPvSeA"
ADMIN_ID = 6468626005
CHANNEL_USERNAME = "1004212833348" # Поменяй на юзернейм своего канала

logging.basicConfig(level=logging.INFO)
router = Router()

def init_db():
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS pets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, status TEXT)")
    conn.commit()
    conn.close()

init_db()

class AdminStates(StatesGroup):
    waiting_for_pet_name = State()
    waiting_for_pet_price = State()
    waiting_for_broadcast = State()
    waiting_for_user_id = State()
    waiting_for_user_amount = State()

def get_main_keyboard(is_admin: bool):
    kb = [
        [KeyboardButton(text="📦 Каталог петов"), KeyboardButton(text="💰 Мой баланс")],
        [KeyboardButton(text="👤 Связь с продавцом")]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить пета", callback_data="add_pet")],
            [InlineKeyboardButton(text="🗑 Удалить пета", callback_data="del_pet_list")],
            [InlineKeyboardButton(text="💳 Выдать монеты", callback_data="give_money")],
            [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="broadcast")],
        ]
    )

@router.message(Command("start"))
async def cmd_start(message: Message):
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("🐾 Привет! Добро пожаловать в магазин петов Adopt Me!", reply_markup=get_main_keyboard(message.from_user.id == ADMIN_ID))

@router.message(F.text == "💰 Мой баланс")
async def show_balance(message: Message):
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()
    conn.close()
    balance = res[0] if res else 0
    await message.answer(f"💳 Твой баланс: **{balance} монет**", parse_mode="Markdown")

@router.message(F.text == "📦 Каталог петов")
async def show_catalog(message: Message):
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price FROM pets")
    pets = cursor.fetchall()
    conn.close()
    if not pets: await message.answer("😔 Каталог пока пуст."); return
    for p in pets:
        await message.answer(f"🐾 **{p[1]}**\n💵 Цена: **{p[2]} монет**", 
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{p[0]}")]]), parse_mode="Markdown")

@router.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery, bot: Bot):
    pet_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    cursor.execute("SELECT name, price FROM pets WHERE id = ?", (pet_id,))
    pet = cursor.fetchone()

    if pet and balance >= pet[1]:
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (pet[1], user_id))
        cursor.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
        conn.commit()
        await callback.message.edit_text(f"✅ Успешно! Ты купил **{pet[0]}**. Напиши админу для получения.")
        await bot.send_message(ADMIN_ID, f"🚨 **Покупка!** {callback.from_user.full_name} купил {pet[0]}")
    else:
        await callback.answer("❌ Не хватает монет или пет продан!", show_alert=True)
    conn.close()

# --- АДМИН ХЕНДЛЕРЫ ---
@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 Панель управления:", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "give_money")
async def start_give_money(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID пользователя:")
    await state.set_state(AdminStates.waiting_for_user_id)

@router.message(AdminStates.waiting_for_user_id)
async def get_id(message: Message, state: FSMContext):
    await state.update_data(uid=int(message.text))
    await message.answer("Введите сумму:")
    await state.set_state(AdminStates.waiting_for_user_amount)

@router.message(AdminStates.waiting_for_user_amount)
async def get_amount(message: Message, state: FSMContext):
    amount = int(message.text)
    uid = (await state.get_data())['uid']
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Готово!")

@router.callback_query(F.data == "add_pet")
async def add_pet(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Название пета:")
    await state.set_state(AdminStates.waiting_for_pet_name)

@router.message(AdminStates.waiting_for_pet_name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Цена:")
    await state.set_state(AdminStates.waiting_for_pet_price)

@router.message(AdminStates.waiting_for_pet_price)
async def add_price(message: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pets (name, price, status) VALUES (?, ?, ?)", (data['name'], int(message.text), "В наличии"))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Добавлено!")

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

