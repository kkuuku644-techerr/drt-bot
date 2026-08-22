import asyncio, logging, sqlite3, time
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import *

TOKEN = "8981643006:AAFoHeKbNAuUuQdgMwYq2_7jUSi5JVPvSeA"
ADMIN_IDS = [6468626005, 7959524856]
REVIEWS_LINK = "https://t.me/+xxzJbxrmH440Y2Zi"

logging.basicConfig(level=logging.INFO)
router = Router()

class AdminSG(StatesGroup):
    add_name = State(); add_price = State(); add_stock = State()
    give_id = State(); give_amt = State()

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

# --- КЛАВИАТУРЫ ---
def kb_main(uid):
    kb = [[KeyboardButton(text="📦 Каталог"), KeyboardButton(text="💰 Баланс")],
          [KeyboardButton(text="📜 Мои покупки"), KeyboardButton(text="💬 Отзывы")],
          [KeyboardButton(text="🎁 Активировать промо")]]
    if uid in ADMIN_IDS: kb.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- FSM ДЛЯ ПРОМО ---
class PromoSG(StatesGroup): wait_code = State()

@router.message(Command("start"))
async def start(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (msg.from_user.id,))
    conn.commit(); conn.close()
    await msg.answer("🐾 Добро пожаловать!", reply_markup=kb_main(msg.from_user.id))

@router.message(F.text == "🎁 Активировать промо")
async def ask_promo(msg: Message, state: FSMContext):
    await msg.answer("Введите код:")
    await state.set_state(PromoSG.wait_code)

@router.message(PromoSG.wait_code)
async def check_promo(msg: Message, state: FSMContext):
    code = msg.text; uid = msg.from_user.id
    conn = sqlite3.connect("adopt_shop.db")
    p = conn.execute("SELECT amount FROM promos WHERE code = ?", (code,)).fetchone()
    if p:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (p[0], uid))
        conn.execute("DELETE FROM promos WHERE code = ?", (code,))
        await msg.answer(f"🎉 +{p[0]} монет!")
    else:
        v = conn.execute("SELECT days FROM vip_promos WHERE code = ?", (code,)).fetchone()
        if v:
            curr = conn.execute("SELECT vip_expires FROM users WHERE user_id = ?", (uid,)).fetchone()[0]
            exp = (max(curr, time.time())) + v[0]*86400
            conn.execute("UPDATE users SET vip_expires = ? WHERE user_id = ?", (int(exp), uid))
            conn.execute("DELETE FROM vip_promos WHERE code = ?", (code,))
            await msg.answer("👑 VIP активирован!")
        else: await msg.answer("❌ Неверный код.")
    conn.commit(); conn.close(); await state.clear()

# --- АДМИНКА ---
@router.message(F.text == "⚙️ Админ-панель", F.from_user.id.in_(ADMIN_IDS))
async def adm(msg: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Добавить пета"), KeyboardButton(text="💰 Выдать монеты")],
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)
    await msg.answer("Админ-панель:", reply_markup=kb)

@router.message(F.text == "➕ Добавить пета", F.from_user.id.in_(ADMIN_IDS))
async def add_p(msg: Message, state: FSMContext): await msg.answer("Название:") or await state.set_state(AdminSG.add_name)

@router.message(AdminSG.add_name)
async def p2(msg: Message, state: FSMContext): await state.update_data(n=msg.text) or await msg.answer("Цена:") or await state.set_state(AdminSG.add_price)

@router.message(AdminSG.add_price)
async def p3(msg: Message, state: FSMContext): await state.update_data(p=msg.text) or await msg.answer("Кол-во:") or await state.set_state(AdminSG.add_stock)

@router.message(AdminSG.add_stock)
async def p4(msg: Message, state: FSMContext):
    d = await state.get_data(); conn = sqlite3.connect("adopt_shop.db")
    conn.execute("INSERT INTO pets (name, price, stock) VALUES (?, ?, ?)", (d['n'], d['p'], msg.text))
    conn.commit(); conn.close(); await state.clear(); await msg.answer("✅ Добавлено!")

@router.message(Command("addpromo"), F.from_user.id.in_(ADMIN_IDS))
async def ap(msg: Message):
    a = msg.text.split(); conn = sqlite3.connect("adopt_shop.db")
    conn.execute("INSERT INTO promos VALUES (?, ?)", (a[1], a[2])); conn.commit(); conn.close(); await msg.answer("✅")

@router.message(Command("addvipromo"), F.from_user.id.in_(ADMIN_IDS))
async def av(msg: Message):
    a = msg.text.split(); conn = sqlite3.connect("adopt_shop.db")
    conn.execute("INSERT INTO vip_promos VALUES (?, ?)", (a[1], a[2])); conn.commit(); conn.close(); await msg.answer("✅")

# --- ОСТАЛЬНОЕ (Каталог, покупки и т.д. как в прошлый раз) ---
@router.message(F.text == "📦 Каталог")
async def cat(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    pets = conn.execute("SELECT id, name, price, stock FROM pets WHERE stock > 0").fetchall()
    conn.close()
    for p in pets: await msg.answer(f"🐾 {p[1]} | 💵 {p[2]} монет | 📦 {p[3]} шт", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{p[0]}")]]))

@router.callback_query(F.data.startswith("buy_"))
async def buy(call: CallbackQuery):
    pid = int(call.data.split("_")[1]); conn = sqlite3.connect("adopt_shop.db")
    u = conn.execute("SELECT balance, vip_expires FROM users WHERE user_id = ?", (call.from_user.id,)).fetchone()
    p = conn.execute("SELECT name, price FROM pets WHERE id = ?", (pid,)).fetchone()
    pr = int(p[1]*0.9) if u[1]>time.time() else p[1]
    if u[0]>=pr:
        conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (pr, call.from_user.id))
        conn.execute("UPDATE pets SET stock = stock - 1 WHERE id = ?", (pid,))
        conn.execute("INSERT INTO purchases (user_id, pet_name, price, date) VALUES (?, ?, ?, ?)", (call.from_user.id, p[0], pr, time.strftime("%d.%m %H:%M")))
        conn.commit(); await call.message.edit_text(f"✅ Куплено: {p[0]}")
    else: await call.answer("❌ Не хватает монет!")
    conn.close()

@router.message(F.text == "💰 Баланс")
async def bal(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    u = conn.execute("SELECT balance, vip_expires FROM users WHERE user_id = ?", (msg.from_user.id,)).fetchone()
    conn.close(); await msg.answer(f"💳 Баланс: {u[0]}\n👑 VIP: {'Активен' if u[1]>time.time() else 'Нет'}")

@router.message(F.text == "📜 Мои покупки")
async def hist(msg: Message):
    conn = sqlite3.connect("adopt_shop.db")
    h = conn.execute("SELECT pet_name, price, date FROM purchases WHERE user_id = ?", (msg.from_user.id,)).fetchall()
    conn.close(); await msg.answer("\n".join([f"🐾 {i[0]} ({i[1]} м.)" for i in h]) or "Пусто.")

@router.message(F.text == "💬 Отзывы")
async def rev(msg: Message): await msg.answer(f"💬 Отзывы: {REVIEWS_LINK}")

@router.message(F.text == "⬅️ Назад")
async def back(msg: Message): await msg.answer("Главное меню:", reply_markup=kb_main(msg.from_user.id))

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())

