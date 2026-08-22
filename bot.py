import asyncio
import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import *

# --- КОНФИГ ---
TOKEN = "8981643006:AAEsMTg_5n_o0TCntiZ4uBNHPxubO6iRlH0"
ADMIN_IDS = [6468626005, 7959524856]
SELLER_USERNAME = "Whars12"

logging.basicConfig(level=logging.INFO)
router = Router()

def init_db():
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, vip_expires INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS pets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, stock INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER)")
    conn.commit()
    conn.close()

init_db()

# --- FSM СОСТОЯНИЯ ---
class AdminStates(StatesGroup):
    add_pet_name = State()
    add_pet_price = State()
    add_pet_stock = State()
    add_promo_code = State()
    add_promo_amount = State()
    give_money_id = State()
    give_money_amount = State()
    give_vip_id = State()

# --- КЛАВИАТУРЫ ---
def get_main_kb(uid):
    kb = [[KeyboardButton(text="📦 Каталог"), KeyboardButton(text="💰 Баланс")]]
    if uid in ADMIN_IDS: kb.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить пета", callback_data="adm_addpet")],
        [InlineKeyboardButton(text="🎁 Создать промо", callback_data="adm_addpromo")],
        [InlineKeyboardButton(text="💰 Выдать монеты", callback_data="adm_money")],
        [InlineKeyboardButton(text="👑 Выдать VIP", callback_data="adm_vip")]
    ])

# --- ЛОГИКА ---
@router.message(Command("start"))
async def start(msg: Message):
    await msg.answer("🐾 Добро пожаловать!", reply_markup=get_main_kb(msg.from_user.id))

@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel(msg: Message):
    if msg.from_user.id in ADMIN_IDS:
        await msg.answer("🛠 Панель управления:", reply_markup=get_admin_kb())

# --- АДМИН ДЕЙСТВИЯ (Кнопки) ---
@router.callback_query(F.data.startswith("adm_"))
async def admin_actions(call: CallbackQuery, state: FSMContext):
    if call.data == "adm_addpet":
        await call.message.answer("Введите название пета:")
        await state.set_state(AdminStates.add_pet_name)
    elif call.data == "adm_money":
        await call.message.answer("Введите ID пользователя:")
        await state.set_state(AdminStates.give_money_id)
    elif call.data == "adm_vip":
        await call.message.answer("Введите ID пользователя для выдачи VIP на 30 дней:")
        await state.set_state(AdminStates.give_vip_id)
    await call.answer()

# Добавление пета (пошагово)
@router.message(AdminStates.add_pet_name)
async def pet_n(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("Введите цену:")
    await state.set_state(AdminStates.add_pet_price)

@router.message(AdminStates.add_pet_price)
async def pet_p(msg: Message, state: FSMContext):
    await state.update_data(price=msg.text)
    await msg.answer("Введите количество (сток):")
    await state.set_state(AdminStates.add_pet_stock)

@router.message(AdminStates.add_pet_stock)
async def pet_s(msg: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pets (name, price, stock) VALUES (?, ?, ?)", (data['name'], data['price'], msg.text))
    conn.commit()
    conn.close()
    await state.clear()
    await msg.answer("✅ Пет добавлен!")

# Выдача монет
@router.message(AdminStates.give_money_id)
async def gm_id(msg: Message, state: FSMContext):
    await state.update_data(uid=msg.text)
    await msg.answer("Сумма:")
    await state.set_state(AdminStates.give_money_amount)

@router.message(AdminStates.give_money_amount)
async def gm_amt(msg: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (msg.text, data['uid']))
    conn.commit()
    conn.close()
    await state.clear()
    await msg.answer("✅ Монеты начислены!")

# Выдача VIP
@router.message(AdminStates.give_vip_id)
async def give_vip(msg: Message, state: FSMContext):
    expires = int(time.time() + 30 * 24 * 60 * 60)
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET vip_expires = ? WHERE user_id = ?", (expires, msg.text))
    conn.commit()
    conn.close()
    await state.clear()
    await msg.answer("👑 VIP выдан на месяц!")

# --- ПОКУПКА ---
@router.callback_query(F.data.startswith("buy_"))
async def buy(call: CallbackQuery, bot: Bot):
    uid = call.from_user.id
    pid = int(call.data.split("_")[1])
    conn = sqlite3.connect("adopt_shop.db")
    cur = conn.cursor()
    cur.execute("SELECT balance, vip_expires FROM users WHERE user_id = ?", (uid,))
    user = cur.fetchone()
    cur.execute("SELECT name, price, stock FROM pets WHERE id = ?", (pid,))
    pet = cur.fetchone()

    # VIP скидка 10%
    price = int(pet[1] * 0.9) if user[1] > time.time() else pet[1]

    if user[0] >= price and pet[2] > 0:
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, uid))
        cur.execute("UPDATE pets SET stock = stock - 1 WHERE id = ?", (pid,))
        conn.commit()
        await call.message.edit_text(f"✅ Куплено: {pet[0]}!")
        # Уведомление админам
        for aid in ADMIN_IDS:
            await bot.send_message(aid, f"🚨 Покупка {pet[0]} от {call.from_user.full_name}", 
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Написать", url=f"tg://user?id={uid}")]]))
    else:
        await call.answer("❌ Нет монет или товара!", show_alert=True)
    conn.close()

# Запуск
async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

