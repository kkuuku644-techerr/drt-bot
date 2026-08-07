import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random, json, os

TOKEN = "8935480244:AAH3w6vUIkQTnKD93SCBL8QiwIDKF7NS4kq"
VIP_PRICE = 30
PASSPORT_CHAT_ID = -1004409308961
DATA_FILE = "data.json"
ADMIN_CHAT_ID = -1004410094117
CHANNEL Iimport logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random, json, os

TOKEN = "ВАШ_ТОКЕН"
VIP_PRICE = 100
PASSPORT_CHAT_ID = -1001234567890
DATA_FILE = "data.json"
CHANNEL_ID = 1004404647295

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "vip": set()}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

def get_user(user_id):
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {"balance": 1000, "total_bet": 0}
        save_data()
    return data["users"][uid]

def is_vip(user_id):
    return str(user_id) in data["vip"]

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 Слот", callback_data="slot"), InlineKeyboardButton("🎲 Кости", callback_data="dice")],
        [InlineKeyboardButton("🃏 Блэкджек", callback_data="blackjack"), InlineKeyboardButton("🏆 VIP", callback_data="vip")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(f"Добро пожаловать!\nБаланс: {user['balance']}💰", reply_markup=main_menu())

async def passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != PASSPORT_CHAT_ID or not context.args:
        return
    await update.message.reply_text(f"Паспорт выдан {context.args[0]}")

async def slot_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    bet = 10
    if user["balance"] < bet:
        await update.callback_query.answer("Недостаточно!", show_alert=True)
        return
    user["balance"] -= bet
    result = random.choices(["🍒","🍋","🔔","💎","7️⃣"], weights=[30,30,20,15,5])[0]
    win = bet*3 if result=="💎" else bet*5 if result=="7️⃣" else bet*2 if result=="🔔" else 0
    user["balance"] += win
    save_data()
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"🎰 {result}\nСтавка: {bet}\nВыигрыш: {win}\nБаланс: {user['balance']}💰", reply_markup=main_menu())

async def dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    bet = 10
    if user["balance"] < bet:
        await update.callback_query.answer("Недостаточно!", show_alert=True)
        return
    user["balance"] -= bet
    p, b = random.randint(1,6), random.randint(1,6)
    win = bet*2 if p>b else bet if p==b else 0
    user["balance"] += win
    save_data()
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"🎲 Вы: {p} | Бот: {b}\nСтавка: {bet}\nВыигрыш: {win}\nБаланс: {user['balance']}💰", reply_markup=main_menu())

async def blackjack_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    bet = 10
    if user["balance"] < bet:
        await update.callback_query.answer("Недостаточно!", show_alert=True)
        return
    user["balance"] -= bet
    p, d = random.randint(12,21), random.randint(12,21)
    win = bet*2 if p>d and p<=21 else bet if p==d else bet*3 if p==21 and d!=21 else 0
    user["balance"] += win
    save_data()
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"🃏 Вы: {p} | Дилер: {d}\nСтавка: {bet}\nВыигрыш: {win}\nБаланс: {user['balance']}💰", reply_markup=main_menu())

async def vip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if is_vip(user_id):
        await update.callback_query.answer("Вы уже VIP!")
        return
    if user["balance"] < VIP_PRICE:
        await update.callback_query.answer(f"Нужно {VIP_PRICE}💰", show_alert=True)
        return
    user["balance"] -= VIP_PRICE
    data["vip"].add(str(user_id))
    user["balance"] += 50
    save_data()
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🏆 Вы стали VIP! +50 бонус", reply_markup=main_menu())

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"👤 Профиль\nБаланс: {user['balance']}💰\nVIP: {'✅' if is_vip(user_id) else '❌'}\nСтавок: {user['total_bet']}", reply_markup=main_menu())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("passport", passport))
    for cb in ["slot","dice","blackjack","vip","profile"]:
        app.add_handler(CallbackQueryHandler(globals()[f"{cb}_game" if cb in ["slot","dice","blackjack"] else f"{cb}_handler"], pattern=cb))
    app.run_polling()

if name == "main":
    main(

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "vip": set()}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

def get_user(user_id):
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {"balance": 1000, "total_bet": 0}
        save_data()
    return data["users"][uid]

def is_vip(user_id):
    return str(user_id) in data["vip"]

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 Слот", callback_data="slot"), InlineKeyboardButton("🎲 Кости", callback_data="dice")],
        [InlineKeyboardButton("🃏 Блэкджек", callback_data="blackjack"), InlineKeyboardButton("🏆 VIP", callback_data="vip")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(f"Добро пожаловать!\nБаланс: {user['balance']}💰", reply_markup=main_menu())

async def passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != PASSPORT_CHAT_ID or not context.args:
        return
    await update.message.reply_text(f"Паспорт выдан {context.args[0]}")

async def slot_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    bet = 10
    if user["balance"] < bet:
        await update.callback_query.answer("Недостаточно!", show_alert=True)
        return
    user["balance"] -= bet
    result = random.choices(["🍒","🍋","🔔","💎","7️⃣"], weights=[30,30,20,15,5])[0]
    win = bet*3 if result=="💎" else bet*5 if result=="7️⃣" else bet*2 if result=="🔔" else 0
    user["balance"] += win
    save_data()
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"🎰 {result}\nСтавка: {bet}\nВыигрыш: {win}\nБаланс: {user['balance']}💰", reply_markup=main_menu())

async def dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    bet = 10
    if user["balance"] < bet:
        await update.callback_query.answer("Недостаточно!", show_alert=True)
        return
    user["balance"] -= bet
    p, b = random.randint(1,6), random.randint(1,6)
    win = bet*2 if p>b else bet if p==b else 0
    user["balance"] += win
    save_data()
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"🎲 Вы: {p} | Бот: {b}\nСтавка: {bet}\nВыигрыш: {win}\nБаланс: {user['balance']}💰", reply_markup=main_menu())

async def blackjack_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    bet = 10
    if user["balance"] < bet:
        await update.callback_query.answer("Недостаточно!", show_alert=True)
        return
    user["balance"] -= bet
    p, d = random.randint(12,21), random.randint(12,21)
    win = bet*2 if p>d and p<=21 else bet if p==d else bet*3 if p==21 and d!=21 else 0
    user["balance"] += win
    save_data()
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"🃏 Вы: {p} | Дилер: {d}\nСтавка: {bet}\nВыигрыш: {win}\nБаланс: {user['balance']}💰", reply_markup=main_menu())

async def vip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if is_vip(user_id):
        await update.callback_query.answer("Вы уже VIP!")
        return
    if user["balance"] < VIP_PRICE:
        await update.callback_query.answer(f"Нужно {VIP_PRICE}💰", show_alert=True)
        return
    user["balance"] -= VIP_PRICE
    data["vip"].add(str(user_id))
    user["balance"] += 50
    save_data()
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🏆 Вы стали VIP! +50 бонус", reply_markup=main_menu())

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"👤 Профиль\nБаланс: {user['balance']}💰\nVIP: {'✅' if is_vip(user_id) else '❌'}\nСтавок: {user['total_bet']}", reply_markup=main_menu())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("passport", passport))
    for cb in ["slot","dice","blackjack","vip","profile"]:
        app.add_handler(CallbackQueryHandler(globals()[f"{cb}_game" if cb in ["slot","dice","blackjack"] else f"{cb}_handler"], pattern=cb))
    app.run_polling()

if name == "main":
    main()
