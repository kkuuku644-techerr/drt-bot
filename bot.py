import asyncio, logging, sqlite3, time
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import *

TOKEN = "8981643006:AAHv-k8X2Q7U1Tj8MfR92Hh1WDfCAMOUbr4"
ADMIN_IDS = [6468626005, 7959524856]
REVIEWS_LINK = "https://t.me/+xxzJbxrmH440Y2Zi"

logging.basicConfig(level=logging.INFO)
router = Router()

class AdminSG(StatesGroup):
    add_name = State(); add_price = State(); add_stock = State()
    give_id = State(); give_amt = State()

class PromoSG(StatesGroup): wait_code = State()

def init_db():
    conn = sqlite3.connect("adopt_shop.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, vip_expires INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS pets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, stock INTEGER DEFAULT 1)")
    cur.execute("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS vip_promos (code TEXT PRIMARY KEY, days INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, pet_name TEXT, price INTEGER, date TEXT)")
    conn.commit(); conn.close()

init_db()

def kb_main(uid):
    kb = [[KeyboardButton(text="📦 Каталог"), KeyboardButton(text="💰 Баланс")],
          [KeyboardButton(text="📜 Мои покупки"), KeyboardButton(text="💬 Отзывы")],
          [KeyboardButton(text="🎁 Активировать промо")]]
    if uid in ADMIN_IDS: kb.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def kb_admin():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Добавить пета"), KeyboardButton(text="💰 Выдать монеты")],
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)

@router.message(Command("start"))
async def start(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (msg.from_user.id,))
    conn.commit(); conn.close()
    await msg.answer("🐾 Добро пожаловать!", reply_markup=kb_main(msg.from_user.id))

# --- КАТАЛОГ ---
@router.message(F.text == "📦 Каталог")
async def cat(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    pets = conn.execute("SELECT id, name, price, stock FROM pets WHERE stock > 0").fetchall()
    conn.close()
    if not pets:
        await msg.answer("😔 Каталог пока пуст.")
        return
    for p in pets:
        await msg.answer(
            f"🐾 **{p[1]}**\n💵 Цена: {p[2]} монет\n📦 В наличии: {p[3]} шт.", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{p[0]}")]]),
            parse_mode="Markdown"
        )

@router.callback_query(F.data.startswith("buy_"))
async def buy(call: CallbackQuery):
    pid = int(call.data.split("_")[1]); conn = sqlite3.connect("adopt_shop.db")
    u = conn.execute("SELECT balance, vip_expires FROM users WHERE user_id = ?", (call.from_user.id,)).fetchone()
    p = conn.execute("SELECT name, price, stock FROM pets WHERE id = ?", (pid,)).fetchone()
    if not p or p[2] <= 0:
        await call.answer("❌ Товара нет!", show_alert=True)
        conn.close(); return
    pr = int(p[1]*0.9) if u[1]>time.time() else p[1]
    if u[0]>=pr:
        conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (pr, call.from_user.id))
        conn.execute("UPDATE pets SET stock = stock - 1 WHERE id = ?", (pid,))
        conn.execute("INSERT INTO purchases (user_id, pet_name, price, date) VALUES (?, ?, ?, ?)", (call.from_user.id, p[0], pr, time.strftime("%d.%m %H:%M")))
        conn.commit(); await call.message.edit_text(f"✅ Успешно куплено: {p[0]}")
    else: await call.answer("❌ Не хватает монет на балансе!", show_alert=True)
    conn.close()

# --- БАЛАНС И ПОКУПКИ ---
@router.message(F.text == "💰 Баланс")
async def bal(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    u = conn.execute("SELECT balance, vip_expires FROM users WHERE user_id = ?", (msg.from_user.id,)).fetchone()
    conn.close()
    await msg.answer(f"💳 Баланс: {u[0] if u else 0} монет\n👑 VIP: {'Активен' if u and u[1]>time.time() else 'Нет'}")

@router.message(F.text == "📜 Мои покупки")
async def hist(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    h = conn.execute("SELECT pet_name, price, date FROM purchases WHERE user_id = ?", (msg.from_user.id,)).fetchall()
    conn.close()
    text = "\n".join([f"🐾 {i[0]} — {i[1]} монет ({i[2]})" for i in h]) if h else "У тебя пока нет покупок."
    await msg.answer(f"📜 История покупок:\n\n{text}")

@router.message(F.text == "💬 Отзывы")
async def rev(msg: Message): await msg.answer(f"💬 Чат отзывов: {REVIEWS_LINK}")

# --- ПРОМОКОДЫ КНОПКОЙ ---
@router.message(F.text == "🎁 Активировать промо")
async def ask_promo(msg: Message, state: FSMContext):
    await msg.answer("Введите промокод:")
    await state.set_state(PromoSG.wait_code)

@router.message(PromoSG.wait_code)
async def check_promo(msg: Message, state: FSMContext):
    code = msg.text.strip(); uid = msg.from_user.id
    conn = sqlite3.connect("adopt_shop.db")
    p = conn.execute("SELECT amount FROM promos WHERE code = ?", (code,)).fetchone()
    if p:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (p[0], uid))
        conn.execute("DELETE FROM promos WHERE code = ?", (code,))
        await msg.answer(f"🎉 Промокод активирован! Зачислено: +{p[0]} монет.")
    else:
        v = conn.execute("SELECT days FROM vip_promos WHERE code = ?", (code,)).fetchone()
        if v:
            curr = conn.execute("SELECT vip_expires FROM users WHERE user_id = ?", (uid,)).fetchone()[0]
            exp = (max(curr, time.time())) + v[0]*86400
            conn.execute("UPDATE users SET vip_expires = ? WHERE user_id = ?", (int(exp), uid))
            conn.execute("DELETE FROM vip_promos WHERE code = ?", (code,))
            await msg.answer(f"👑 VIP-статус успешно активирован на {v[0]} дней!")
        else: await msg.answer("❌ Промокод недействителен.")
    conn.commit(); conn.close(); await state.clear()

# --- АДМИНКА ---
@router.message(F.text == "⚙️ Админ-панель", F.from_user.id.in_(ADMIN_IDS))
async def adm(msg: Message):
    await msg.answer("🛠 Панель управления:", reply_markup=kb_admin())

@router.message(F.text == "⬅️ Назад")
async def back(msg: Message):
    await msg.answer("Главное меню:", reply_markup=kb_main(msg.from_user.id))

# Добавление пета
@router.message(F.text == "➕ Добавить пета", F.from_user.id.in_(ADMIN_IDS))
async def add_p(msg: Message, state: FSMContext):
    await msg.answer("Введите название пета:")
    await state.set_state(AdminSG.add_name)

@router.message(AdminSG.add_name)
async def p2(msg: Message, state: FSMContext):
    await state.update_data(n=msg.text)
    await msg.answer("Введите цену:")
    await state.set_state(AdminSG.add_price)

@router.message(AdminSG.add_price)
async def p3(msg: Message, state: FSMContext):
    await state.update_data(p=msg.text)
    await msg.answer("Введите количество (сток):")
    await state.set_state(AdminSG.add_stock)

@router.message(AdminSG.add_stock)
async def p4(msg: Message, state: FSMContext):
    d = await state.get_data(); conn = sqlite3.connect("adopt_shop.db")
    conn.execute("INSERT INTO pets (name, price, stock) VALUES (?, ?, ?)", (d['n'], int(d['p']), int(msg.text)))
    conn.commit(); conn.close(); await state.clear()
    await msg.answer("✅ Пет успешно добавлен в магазин!", reply_markup=kb_admin())

# Выдача монет через кнопки
@router.message(F.text == "💰 Выдать монеты", F.from_user.id.in_(ADMIN_IDS))
async def give_m_start(msg: Message, state: FSMContext):
    await msg.answer("Введите Telegram ID пользователя:")
    await state.set_state(AdminSG.give_id)

@router.message(AdminSG.give_id)
async def give_m_id(msg: Message, state: FSMContext):
    await state.update_data(uid=int(msg.text))
    await msg.answer("Введите количество монет для выдачи:")
    await state.set_state(AdminSG.give_amt)

@router.message(AdminSG.give_amt)
async def give_m_finish(msg: Message, state: FSMContext):
    d = await state.get_data(); conn = sqlite3.connect("adopt_shop.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (d['uid'],))
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (int(msg.text), d['uid']))
    conn.commit(); conn.close(); await state.clear()
    await msg.answer("✅ Монеты успешно выданы пользователю!", reply_markup=kb_admin())

# Команды админа для промо (поддерживают и /addvipromo, и /addvippromo)
@router.message(Command("addpromo"), F.from_user.id.in_(ADMIN_IDS))
async def ap(msg: Message):
    a = msg.text.split()
    if len(a) < 3: return await msg.answer("Формат: /addpromo КОД СУММА")
    conn = sqlite3.connect("adopt_shop.db")
    conn.execute("INSERT OR REPLACE INTO promos VALUES (?, ?)", (a[1], int(a[2])))
    conn.commit(); conn.close()
    await msg.answer(f"✅ Промокод на монеты `{a[1]}` на `{a[2]}` монет создан!", parse_mode="Markdown")

@router.message(Command("addvipromo", "addvippromo"), F.from_user.id.in_(ADMIN_IDS))
async def av(msg: Message):
    a = msg.text.split()
    if len(a) < 3: return await msg.answer("Формат: /addvipromo КОД ДНИ")
    conn = sqlite3.connect("adopt_shop.db")
    conn.execute("INSERT OR REPLACE INTO vip_promos VALUES (?, ?)", (a[1], int(a[2])))
    conn.commit(); conn.close()
    await msg.answer(f"👑 VIP-промокод `{a[1]}` на `{a[2]}` дней успешно создан!", parse_mode="Markdown")

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())

