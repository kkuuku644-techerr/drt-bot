import telebot
from telebot import types
import random
import sqlite3
import time
import json
from datetime import datetime, timedelta

# ================= НАСТРОЙКИ =================
TOKEN = "8935480244:AAHeLi0e2Aqe2RA9m2oh8v9vGkHNwSsAPPI"
CHANNEL_ID = -1004404647295
ADMIN_CHAT_ID = -1004410094117
ADMIN_IDS = [7959524856]

START_BALANCE = 1000
START_PIGS = 5
VIP_MULTIPLIER = 2.5
NORMAL_MULTIPLIER = 2.0

# Приписки для паспорта
REQUIRED_TAGS = ['drt', 'd1rty', 'pig.zip']

# Цены за звезды
STAR_PRICES = {
    5: 1000,
    45: 10000,
    65: 15000,
    100: 20000
}

VIP_STARS_PRICE = 25

bot = telebot.TeleBot(TOKEN)

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users
                   (user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 1000,
                    pigs INTEGER DEFAULT 5,
                    is_vip INTEGER DEFAULT 0,
                    vip_until INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0,
                    passport TEXT DEFAULT '')''')
    cur.execute('''CREATE TABLE IF NOT EXISTS settings
                   (key TEXT PRIMARY KEY,
                    value TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS mirrors
                   (user_id INTEGER PRIMARY KEY)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS pending_slips
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    content TEXT,
                    timestamp INTEGER)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS star_purchases
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    stars INTEGER,
                    coins INTEGER,
                    timestamp INTEGER)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (user_id, balance, pigs, passport) VALUES (?, ?, ?, ?)", 
                   (user_id, START_BALANCE, START_PIGS, ''))
        conn.commit()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = cur.fetchone()
    conn.close()
    return user

def update_balance(user_id, amount):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    if amount > 0:
        cur.execute("UPDATE users SET total_earned = total_earned + ? WHERE user_id=?", (amount, user_id))
    else:
        cur.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id=?", (abs(amount), user_id))
    conn.commit()
    conn.close()

def update_pigs(user_id, amount):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET pigs = pigs + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def set_vip(user_id, status, days=30):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    if status:
        vip_until = int((datetime.now() + timedelta(days=days)).timestamp())
        cur.execute("UPDATE users SET is_vip = 1, vip_until = ? WHERE user_id=?", (vip_until, user_id))
    else:
        cur.execute("UPDATE users SET is_vip = 0, vip_until = 0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def check_vip(user_id):
    user = get_user(user_id)
    if user[3] and user[4] > int(time.time()):
        return True
    elif user[3]:
        set_vip(user_id, 0)
        return False
    return False

def set_passport(user_id, passport_data):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET passport = ? WHERE user_id=?", (json.dumps(passport_data), user_id))
    conn.commit()
    conn.close()

def get_passport(user_id):
    user = get_user(user_id)
    if user[6]:
        return json.loads(user[6])
    return {}

def get_setting(key):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    val = cur.fetchone()
    conn.close()
    return val[0] if val else None

def set_setting(key, value):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def add_mirror(user_id):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO mirrors (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def is_mirror(user_id):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM mirrors WHERE user_id=?", (user_id,))
    val = cur.fetchone()
    conn.close()
    return val is not None

def add_pending_slip(user_id, content):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO pending_slips (user_id, content, timestamp) VALUES (?, ?, ?)", 
               (user_id, content, int(time.time())))
    slip_id = cur.lastrowid
    conn.commit()
    conn.close()
    return slip_id

def get_pending_slip(slip_id):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM pending_slips WHERE id=?", (slip_id,))
    slip = cur.fetchone()
    conn.close()
    return slip

def delete_pending_slip(slip_id):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM pending_slips WHERE id=?", (slip_id,))
    conn.commit()
    conn.close()

def log_star_purchase(user_id, stars, coins):
    conn = sqlite3.connect('casino_bot.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO star_purchases (user_id, stars, coins, timestamp) VALUES (?, ?, ?, ?)",
               (user_id, stars, coins, int(time.time())))
    conn.commit()
    conn.close()

# ================= КЛАВИАТУРА МЕНЮ =================
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    btn1 = types.KeyboardButton('🎰 Казино')
    btn2 = types.KeyboardButton('💳 Баланс')
    btn3 = types.KeyboardButton('📋 Паспорт')
    btn4 = types.KeyboardButton('🐷 Свиньи')
    btn5 = types.KeyboardButton('⭐ Магазин')
    btn6 = types.KeyboardButton('📤 Слив')
    keyboard.add(btn1, btn2, btn3)
    keyboard.add(btn4, btn5, btn6)
    return keyboard

def get_casino_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('🎲 Кости')
    btn2 = types.KeyboardButton('🎰 Слоты')
    btn3 = types.KeyboardButton('🪙 Орел/Решка')
    btn4 = types.KeyboardButton('💣 Мины')
    btn5 = types.KeyboardButton('🔙 Назад')
    keyboard.add(btn1, btn2)
    keyboard.add(btn3, btn4)
    keyboard.add(btn5)
    return keyboard

def get_shop_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('🐷 Купить свинью')
    btn2 = types.KeyboardButton('💎 Продать свинью')
    btn3 = types.KeyboardButton('👑 Купить VIP')
    btn4 = types.KeyboardButton('⭐ Купить за звезды')
    btn5 = types.KeyboardButton('🔙 Назад')
    keyboard.add(btn1, btn2)
    keyboard.add(btn3, btn4)
    keyboard.add(btn5)
    return keyboard

def get_star_shop_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('⭐ 5⭐ = 1000💰')
    btn2 = types.KeyboardButton('⭐ 45⭐ = 10000💰')
    btn3 = types.KeyboardButton('⭐ 65⭐ = 15000💰')
    btn4 = types.KeyboardButton('⭐ 100⭐ = 20000💰')
    btn5 = types.KeyboardButton('👑 VIP (25⭐/мес)')
    btn6 = types.KeyboardButton('🔙 Назад')
    keyboard.add(btn1, btn2)
    keyboard.add(btn3, btn4)
    keyboard.add(btn5)
    keyboard.add(btn6)
    return keyboard

# ================= ПРОВЕРКА ПОДПИСКИ =================
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def subscription_required(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if not check_subscription(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{(bot.get_chat(CHANNEL_ID).invite_link or '').split('/')[-1]}"))
            markup.add(types.InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub"))
            bot.send_message(message.chat.id, 
                           "❌ Для использования бота необходимо подписаться на наш канал!",
                           reply_markup=markup)
            return
        return func(message, *args, **kwargs)
    return wrapper

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    if check_subscription(call.from_user.id):
        bot.edit_message_text("✅ Подписка подтверждена! Теперь вы можете использовать бота.",
                            call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
        # Показываем главное меню после подписки
        show_main_menu(call.message.chat.id, call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "❌ Вы все еще не подписаны!", show_alert=True)

# ================= ГЛАВНОЕ МЕНЮ =================
def show_main_menu(chat_id, user_id):
    user = get_user(user_id)
    vip_status = "👑 VIP" if check_vip(user_id) else "💎 Обычный"

    welcome_text = f"""
🎰 <b>ДОБРО ПОЖАЛОВАТЬ В КАЗИНО!</b>
━━━━━━━━━━━━━━━━━━━━━
👤 <b>Профиль:</b>
💰 Баланс: <code>{user[1]}</code> монет
🐷 Свиней: <code>{user[2]}</code>
👑 Статус: <code>{vip_status}</code>
━━━━━━━━━━━━━━━━━━━━━
📌 <i>Используй кнопки ниже для навигации</i>
"""
    bot.send_message(chat_id, welcome_text, parse_mode='HTML', reply_markup=get_main_keyboard())

# ================= ОБРАБОТЧИКИ КНОПОК =================
@bot.message_handler(func=lambda message: message.text == '🔙 Назад')
def back_to_main(message):
    show_main_menu(message.chat.id, message.from_user.id)

@bot.message_handler(func=lambda message: message.text == '🎰 Казино')
@subscription_required
def casino_menu(message):
    bot.send_message(message.chat.id, 
                    "🎰 <b>ВЫБЕРИ ИГРУ</b>\n━━━━━━━━━━━━━━━\n"
                    "🎲 Кости - угадай число\n"
                    "🎰 Слоты - крути барабаны\n"
                    "🪙 Орел/Решка - 50/50\n"
                    "💣 Мины - найди алмаз",
                    parse_mode='HTML', reply_markup=get_casino_keyboard())

@bot.message_handler(func=lambda message: message.text == '💳 Баланс')
@subscription_required
def show_balance(message):
    user = get_user(message.from_user.id)
    vip_status = "👑 VIP" if check_vip(message.from_user.id) else "💎 Обычный"
    bot.send_message(message.chat.id, 
                    f"💳 <b>ТВОЙ БАЛАНС</b>\n━━━━━━━━━━━━━━━\n"
                    f"💰 Монет: <code>{user[1]}</code>\n"
                    f"🐷 Свиней: <code>{user[2]}</code>\n"
                    f"👑 Статус: <code>{vip_status}</code>",
                    parse_mode='HTML', reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == '📋 Паспорт')
@subscription_required
def show_passport(message):
    user_id = message.from_user.id
    passport = get_passport(user_id)

    if not passport:
        bot.send_message(message.chat.id, 
                        "📋 <b>У ТЕБЯ НЕТ ПАСПОРТА</b>\n━━━━━━━━━━━━━━━\n"
                        "Создай паспорт чтобы играть!\n"
                        "Напиши /passport чтобы создать",
                        parse_mode='HTML', reply_markup=get_main_keyboard())
        return

    tags = passport.get('tags', [])
    has_tag = any(tag in tags for tag in REQUIRED_TAGS)
    status_text = "✅ Есть" if has_tag else "❌ Нет"
    vip_status = "👑 VIP" if check_vip(user_id) else "💎 Обычный"

    passport_text = f"""
📋 <b>ТВОЙ ПАСПОРТ</b>
━━━━━━━━━━━━━━━
🆔 ID: <code>{user_id}</code>
👤 Имя: <code>{passport.get('name', 'Не указано')}</code>
🏷️ Приписки: <code>{', '.join(tags) if tags else 'Нет'}</code>
📌 Статус: <code>{status_text}</code>
💎 Уровень: <code>{vip_status}</code>
━━━━━━━━━━━━━━━
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Обновить паспорт", callback_data="update_passport"))
    markup.add(types.InlineKeyboardButton("🏷️ Добавить приписку", callback_data="add_tag"))

    bot.send_message(message.chat.id, passport_text, parse_mode='HTML', 
                    reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '🐷 Свиньи')
@subscription_required
def pigs_menu(message):
    user = get_user(message.from_user.id)
    bot.send_message(message.chat.id, 
                    f"🐷 <b>УПРАВЛЕНИЕ СВИНЬЯМИ</b>\n━━━━━━━━━━━━━━━\n"
                    f"🐷 Свиней: <code>{user[2]}</code>\n"
                    f"💰 Баланс: <code>{user[1]}</code>\n━━━━━━━━━━━━━━━\n"
                    "💰 Купить: 500 монет\n"
                    "💎 Продать: 300 монет",
                    parse_mode='HTML', reply_markup=get_shop_keyboard())

@bot.message_handler(func=lambda message: message.text == '⭐ Магазин')
@subscription_required
def shop_menu(message):
    user = get_user(message.from_user.id)
    bot.send_message(message.chat.id, 
                    f"🏪 <b>МАГАЗИН</b>\n━━━━━━━━━━━━━━━\n"
                    f"💰 Баланс: <code>{user[1]}</code>\n"
                    f"🐷 Свиней: <code>{user[2]}</code>\n━━━━━━━━━━━━━━━\n"
                    "🐷 Свинья - 500 монет\n"
                    "👑 VIP - 5000 монет\n"
                    "⭐ Звезды - лучший курс",
                    parse_mode='HTML', reply_markup=get_shop_keyboard())

@bot.message_handler(func=lambda message: message.text == '📤 Слив')
@subscription_required
def propose_menu(message):
    bot.send_message(message.chat.id, 
                    "📤 <b>ПРЕДЛОЖИТЬ СЛИВ</b>\n━━━━━━━━━━━━━━━\n"
                    "Ответь на сообщение командой:\n"
                    "<code>/propose</code>\n\n"
                    "Или просто отправь мне контент",
                    parse_mode='HTML', reply_markup=get_main_keyboard())

# ================= ОБРАБОТЧИКИ ИГР =================
@bot.message_handler(func=lambda message: message.text == '🎲 Кости')
@subscription_required
def dice_game(message):
    user = get_user(message.from_user.id)
    bet = 50
    if user[1] < bet:
        bot.send_message(message.chat.id, f"❌ Недостаточно монет! Нужно {bet}", 
                        reply_markup=get_casino_keyboard())
        return

    update_balance(message.from_user.id, -bet)
    result = random.randint(1, 6)
    win = result == 6

    if win:
        reward = bet * 3
        update_balance(message.from_user.id, reward)
        bot.send_message(message.chat.id, 
                        f"🎲 <b>ВЫПАЛО: {result}</b>\n━━━━━━━━━━━━━━━\n"
                        f"🎉 ПОБЕДА! +{reward} монет!",
                        parse_mode='HTML', reply_markup=get_casino_keyboard())
    else:
        bot.send_message(message.chat.id, 
                        f"🎲 <b>ВЫПАЛО: {result}</b>\n━━━━━━━━━━━━━━━\n"
                        f"😢 Проигрыш! -{bet} монет",
                        parse_mode='HTML', reply_markup=get_casino_keyboard())

@bot.message_handler(func=lambda message: message.text == '🎰 Слоты')
@subscription_required
def slots_game(message):
    user = get_user(message.from_user.id)
    bet = 100
    if user[1] < bet:
        bot.send_message(message.chat.id, f"❌ Недостаточно монет! Нужно {bet}",
                        reply_markup=get_casino_keyboard())
        return

    update_balance(message.from_user.id, -bet)
    symbols = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣']
    result = [random.choice(symbols) for _ in range(3)]

    if result[0] == result[1] == result[2]:
        if result[0] == '7️⃣':
            reward = bet * 10
        elif result[0] == '💎':
            reward = bet * 5
        else:
            reward = bet * 3
        update_balance(message.from_user.id, reward)
        bot.send_message(message.chat.id, 
                        f"🎰 <b>{' '.join(result)}</b>\n━━━━━━━━━━━━━━━\n"
                        f"🎉 ДЖЕКПОТ! +{reward} монет!",
                        parse_mode='HTML', reply_markup=get_casino_keyboard())
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        reward = bet * 2
        update_balance(message.from_user.id, reward)
        bot.send_message(message.chat.id, 
                        f"🎰 <b>{' '.join(result)}</b>\n━━━━━━━━━━━━━━━\n"
                        f"🎉 Выигрыш! +{reward} монет!",
                        parse_mode='HTML', reply_markup=get_casino_keyboard())
    else:
        bot.send_message(message.chat.id, 
                        f"🎰 <b>{' '.join(result)}</b>\n━━━━━━━━━━━━━━━\n"
                        f"😢 Проигрыш! -{bet} монет",
                        parse_mode='HTML', reply_markup=get_casino_keyboard())

@bot.message_handler(func=lambda message: message.text == '🪙 Орел/Решка')
@subscription_required
def coin_game(message):
    user = get_user(message.from_user.id)
    bet = 25
    if user[1] < bet:
        bot.send_message(message.chat.id, f"❌ Недостаточно монет! Нужно {bet}",
                        reply_markup=get_casino_keyboard())
        return

    update_balance(message.from_user.id, -bet)
    result = random.choice(['Орел', 'Решка'])

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🦅 Орел", callback_data=f"coin_Орел_{bet}"),
        types.InlineKeyboardButton("🪙 Решка", callback_data=f"coin_Решка_{bet}")
    )
    bot.send_message(message.chat.id, "Выбери сторону:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('coin_'))
def coin_callback(call):
    _, choice, bet = call.data.split('_')
    bet = int(bet)
    result = random.choice(['Орел', 'Решка'])

    if choice == result:
        reward = bet * 2
        update_balance(call.from_user.id, reward)
        bot.edit_message_text(f"🪙 <b>{result}</b>\n━━━━━━━━━━━━━━━\n🎉 Угадал! +{reward} монет!",
                            call.message.chat.id, call.message.message_id, parse_mode='HTML')
    else:
        bot.edit_message_text(f"🪙 <b>{result}</b>\n━━━━━━━━━━━━━━━\n😢 Не угадал! -{bet} монет",
                            call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == '💣 Мины')
@subscription_required
def mines_game(message):
    user = get_user(message.from_user.id)
    bet = 200
    if user[1] < bet:
        bot.send_message(message.chat.id, f"❌ Недостаточно монет! Нужно {bet}",
                        reply_markup=get_casino_keyboard())
        return

    multiplier = VIP_MULTIPLIER if check_vip(message.from_user.id) else NORMAL_MULTIPLIER
    update_balance(message.from_user.id, -bet)

    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in range(1, 11):
        markup.add(types.InlineKeyboardButton(f"{i}", callback_data=f"mine_{i}_{bet}_{multiplier}"))

    bot.send_message(message.chat.id, 
                    f"💣 <b>МИНЫ</b>\n━━━━━━━━━━━━━━━\n"
                    f"💰 Ставка: {bet}\n"
                    f"📈 Множитель: x{multiplier}\n"
                    f"Выбери клетку (1-10):",
                    parse_mode='HTML', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('mine_'))
def mine_callback(call):
    _, cell, bet, multiplier = call.data.split('_')
    bet = int(bet)
    multiplier = float(multiplier)
    
    win = random.random() < 0.3
    
    if win:
        reward = int(bet * multiplier)
        update_balance(call.from_user.id, reward)
        bot.edit_message_text(f"💣 <b>Клетка #{cell}</b>\n━━━━━━━━━━━━━━━\n🎉 НАШЕЛ АЛМАЗ! +{reward} монет!",
                            call.message.chat.id, call.message.message_id, parse_mode='HTML')
    else:
        bot.edit_message_text(f"💣 <b>Клетка #{cell}</b>\n━━━━━━━━━━━━━━━\n💥 БУХ! Ты подорвался на мине!",
                            call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    init_db()
    print("Бот успешно запущен!")
    bot.infinity_polling()
