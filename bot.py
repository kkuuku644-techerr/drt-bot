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
TOKEN = "8981643006:AAHv-k8X2Q7U1Tj8MfR92Hh1WDfCAMOUbr4"
ADMIN_IDS = [6468626005, 7959524856]
SELLER_USERNAME = "Whars12"
REVIEWS_LINK = "https://t.me/+xxzJbxrmH440Y2Zi"

logging.basicConfig(level=logging.INFO)
router = Router()

def init_db():
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, vip_expires INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS pets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, stock INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, pet_name TEXT, price INTEGER, date TEXT)")
    conn.commit()
    conn.close()

init_db()

# --- FSM СОСТОЯНИЯ ---
class AdminStates(StatesGroup):
    add_pet_name = State()
    add_pet_price = State()
    add_pet_stock = State()
    give_money_id = State()
    give_money_amount = State()
    give_vip_id = State()

# --- КЛАВИАТУРЫ ---
def get_main_kb(uid):
    kb = [
        [KeyboardButton(text="📦 Каталог"), KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="📜 Мои покупки"), KeyboardButton(text="💬 Отзывы")]
    ]
    if uid in ADMIN_IDS: 
        kb.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить пета", callback_data="adm_addpet")],
        [InlineKeyboardButton(text="💰 Выдать монеты", callback_data="adm_money")],
        [InlineKeyboardButton(text="👑 Выдать VIP", callback_data="adm_vip")]
    ])

# --- ЛОГИКА СТАРТА И МЕНЮ ---
@router.message(Command("start"))
async def start(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (msg.from_user.id,))
    conn.commit()
    conn.close()
    await msg.answer("🐾 Добро пожаловать в магазин петов Adopt Me!", reply_markup=get_main_kb(msg.from_user.id))

@router.message(F.text == "💬 Отзывы")
async def reviews(msg: Message):
    await msg.answer(f"💬 Оставить отзыв или почитать мнение других можно здесь:\n👉 {REVIEWS_LINK}", disable_web_page_preview=True)

@router.message(F.text == "📜 Мои покупки")
async def my_purchases(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT pet_name, price, date FROM purchases WHERE user_id = ?", (msg.from_user.id,))
    history = cursor.fetchall()
    conn.close()

    if not history:
        await msg.answer("📜 У тебя пока нет купленных петов.")
        return

    text = "📜 **Твои прошлые покупки:**\n\n"
    for item in history:
        text += f"🐾 {item[0]} — 💵 {item[1]} монет <i>({item[2]})</i>\n"
    await msg.answer(text, parse_mode="HTML")

@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel(msg: Message):
    if msg.from_user.id in ADMIN_IDS:
        await msg.answer("🛠 Панель управления:", reply_markup=get_admin_kb())

# --- ПРОМОКОДЫ ЧЕРЕЗ КОМАНДЫ ---
@router.message(Command("addpromo"))
async def add_promo(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("⚠️ Формат: /addpromo КОД СУММА")
        return
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO promos (code, amount) VALUES (?, ?)", (args[1], int(args[2])))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Промокод `{args[1]}` на `{args[2]}` монет успешно создан!", parse_mode="Markdown")

@router.message(Command("promo"))
async def use_promo(message: Message):
    args = message.text.split()
    if len(args) < 2: return
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM promos WHERE code = ?", (args[1],))
    res = cursor.fetchone()
    if res:
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (res[0], message.from_user.id))
        cursor.execute("DELETE FROM promos WHERE code = ?", (args[1],))
        conn.commit()
        await message.answer(f"🎉 Промокод активирован! Зачислено: +{res[0]} монет.")
    else:
        await message.answer("❌ Промокод недействителен или уже был использован.")
    conn.close()

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

# Добавление пета
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
    await msg.answer("✅ Пет успешно добавлен в магазин!")

# Выдача монет
@router.message(AdminStates.give_money_id)
async def gm_id(msg: Message, state: FSMContext):
    await state.update_data(uid=msg.text)
    await msg.answer("Введите сумму монет:")
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
    await msg.answer("✅ Монеты успешно начислены пользователю!")

# Выдача VIP на 30 дней
@router.message(AdminStates.give_vip_id)
async def give_vip(msg: Message, state: FSMContext):
    expires = int(time.time() + 30 * 24 * 60 * 60)
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET vip_expires = ? WHERE user_id = ?", (expires, msg.text))
    conn.commit()
    conn.close()
    await state.clear()
    await msg.answer("👑 VIP-статус успешно выдан на 30 дней!")

# --- КАТАЛОГ И ПОКУПКА ---
@router.message(F.text == "📦 Каталог")
async def show_catalog(message: Message):
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, stock FROM pets WHERE stock > 0")
    pets = cursor.fetchall()
    conn.close()
    if not pets: 
        await message.answer("😔 Каталог пока пуст.")
        return
    for p in pets:
        await message.answer(
            f"🐾 **{p[1]}**\n💵 Цена: **{p[2]} монет**\n📦 В наличии: {p[3]} шт.", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{p[0]}")]
            ]), 
            parse_mode="Markdown"
        )

@router.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    conn = sqlite3.connect("adopt_shop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, vip_expires FROM users WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()
    conn.close()
    balance = res[0] if res else 0
    vip_status = "👑 Активен" if res and res[1] > time.time() else "❌ Нет"
    await message.answer(f"💳 Твой баланс: **{balance} монет**\nVIP-статус: {vip_status}", parse_mode="Markdown")

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

    if not pet or pet[2] <= 0:
        await call.answer("❌ Товара больше нет в наличии!", show_alert=True)
        conn.close()
        return

    # VIP скидка 10%
    price = int(pet[1] * 0.9) if user[1] > time.time() else pet[1]

    if user[0] >= price:
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, uid))
        cur.execute("UPDATE pets SET stock = stock - 1 WHERE id = ?", (pid,))

        # Запись в историю покупок
        current_date = time.strftime("%d.%m.%Y %H:%M", time.localtime())
        cur.execute("INSERT INTO purchases (user_id, pet_name, price, date) VALUES (?, ?, ?, ?)", (uid, pet[0], price, current_date))
        conn.commit()

        await call.message.edit_text(f"✅ Успешно! Ты купил **{pet[0]}**. Админы уже получили уведомление и скоро свяжутся с тобой!", parse_mode="Markdown")

        # Уведомление админам
        for aid in ADMIN_IDS:
            await bot.send_message(
                aid, 
                f"🚨 **Новая покупка!**\n\n👤 Покупатель: {call.from_user.full_name}\n🐾 Пет: {pet[0]}\n💵 Цена: {price} монет", 
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Написать покупателю", url=f"tg://user?id={uid}")]]),
                parse_mode="Markdown"
            )
    else:
        await call.answer("❌ Не хватает монет на балансе!", show_alert=True)
    conn.close()

# Запуск
async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

