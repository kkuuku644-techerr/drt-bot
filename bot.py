import json
import random
import sqlite3
import time
import telebot
from telebot import types

TOKEN = "8935480244:AAH3w6vUIkQTnKD9eSCBL8QiwIDKF7NS4kg"
CHANNEL_ID = -1004404647295
ADMIN_CHAT_ID = -1004410094117
ADMIN_IDS = [7959524856]

REQUIRED_TAGS = ['drt', 'd1rty', 'pig.zip']

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users
                   (user_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    balance INTEGER DEFAULT 1000,
                    pigs INTEGER DEFAULT 5,
                    is_vip INTEGER DEFAULT 0,
                    vip_expire INTEGER DEFAULT 0,
                    passport TEXT DEFAULT '')''')
    conn.commit()
    conn.close()

def get_user(user_id, username=''):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cur.fetchone()
    now = int(time.time())

    if not user:
        cur.execute("INSERT INTO users (user_id, username, balance, pigs, is_vip, vip_expire, passport) VALUES (?, ?, ?, ?, 0, 0, ?)", 
                   (user_id, username, 1000, 5, ''))
        conn.commit()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = cur.fetchone()
    else:
        if user[4] == 1 and user[5] > 0 and now > user[5]:
            cur.execute("UPDATE users SET is_vip = 0, vip_expire = 0 WHERE user_id=?", (user_id,))
            conn.commit()
            cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            user = cur.fetchone()

        if username and user[1] != username:
            cur.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
            conn.commit()
    conn.close()
    return user

def update_balance(user_id, amount):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def update_pigs(user_id, amount):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET pigs = pigs + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def set_vip_status(user_id, days=30):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    expire_time = int(time.time()) + (days * 24 * 60 * 60)
    cur.execute("UPDATE users SET is_vip = 1, vip_expire = ? WHERE user_id=?", (expire_time, user_id))
    conn.commit()
    conn.close()

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🎰 Казино', '📋 Паспорт')
    markup.add('⭐ VIP за звезды', '📤 Слив')
    return markup

def get_casino_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🎲 Кости', '🎰 Слоты')
    markup.add('💣 Мины', '🔙 Назад')
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    get_user(message.from_user.id, message.from_user.username or '')
    bot.send_message(message.chat.id, "🎰 <b>Главное меню:</b>", parse_mode='HTML', reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == '🔙 Назад')
def back_to_main(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['б'])
def balance_command(message):
    target_user = message.from_user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user

    user = get_user(target_user.id, target_user.username or '')
    now = int(time.time())
    is_active_vip = user[4] == 1 and (user[5] == 0 or user[5] > now)
    vip = "👑 Да" if is_active_vip else "❌ Нет"
    uname = f"@{target_user.username}" if target_user.username else "Нет юзернейма"

    text = (f"💳 <b>Баланс игрока:</b>\n"
            f"👤 Имя: {target_user.first_name}\n"
            f"🔗 Юзер: {uname}\n"
            f"🆔 ID: <code>{target_user.id}</code>\n"
            f"💰 Монеты: <code>{user[2]}</code>\n"
            f"🐷 Свиньи: <code>{user[3]}</code>\n"
            f"👑 VIP статус: {vip}")
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['п'])
def transfer_coins(message):
    if not message.reply_to_message:
        bot.send_message(message.chat.id, "❌ Ответь этой командой на сообщение игрока, которому хочешь перевести монеты! Пример: <code>/п 500</code>", parse_mode='HTML')
        return

    try:
        args = message.text.split()
        amount = int(args[1])
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "❌ Укажи сумму! Пример: <code>/п 500</code>", parse_mode='HTML')
        return

    sender_id = message.from_user.id
    receiver_id = message.reply_to_message.from_user.id

    if sender_id == receiver_id:
        bot.send_message(message.chat.id, "❌ Нельзя переводить монеты самому себе!")
        return

    sender = get_user(sender_id, message.from_user.username or '')
    if sender[2] < amount:
        bot.send_message(message.chat.id, "❌ Недостаточно монет для перевода!")
        return

    get_user(receiver_id, message.reply_to_message.from_user.username or '')

    update_balance(sender_id, -amount)
    update_balance(receiver_id, amount)

    bot.send_message(message.chat.id, f"✅ Успешно переведено <code>{amount}</code> монет игроку!", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '🎰 Казино')
def casino_menu(message):
    bot.send_message(message.chat.id, "🎰 <b>Казино:</b> Выбирай игру:", parse_mode='HTML', reply_markup=get_casino_keyboard())

@bot.message_handler(func=lambda m: m.text == '🎲 Кости')
def dice_game(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username or '')
    bet = 50
    if user[2] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно монет!")
        return
    update_balance(user_id, -bet)
    res = random.randint(1, 6)
    if res >= 4:
        win = bet * 2
        update_balance(user_id, win)
        bot.send_message(message.chat.id, f"🎲 Выпало: {res}\n🎉 Победа! +{win} монет!")
    else:
        bot.send_message(message.chat.id, f"🎲 Выпало: {res}\n😢 Проигрыш! -{bet} монет")

@bot.message_handler(func=lambda m: m.text == '🎰 Слоты')
def slots_game(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username or '')
    bet = 100
    if user[2] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно монет!")
        return
    update_balance(user_id, -bet)
    symbols = ['🍒', '🍋', '7️⃣', '💎']
    res = [random.choice(symbols) for _ in range(3)]
    if res[0] == res[1] == res[2]:
        win = bet * 5
        update_balance(user_id, win)
        text = f"🎰 {' '.join(res)}\n🎉 ДЖЕКПОТ! +{win} монет!"
    elif res[0] == res[1] or res[1] == res[2]:
        win = bet * 2
        update_balance(user_id, win)
        text = f"🎰 {' '.join(res)}\n🎉 Выигрыш! +{win} монет!"
    else:
        text = f"🎰 {' '.join(res)}\n😢 Проигрыш -{bet} монет"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '💣 Мины')
def mines_game(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username or '')
    bet = 200
    if user[2] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно монет!")
        return
    update_balance(user_id, -bet)
    markup = types.InlineKeyboardMarkup(row_width=3)
    for i in range(1, 10):
        markup.add(types.InlineKeyboardButton(f"📦 {i}", callback_data=f"mine_{i}_{bet}"))
    bot.send_message(message.chat.id, f"💣 <b>Мины (Квадрат 3x3)</b>\nСтавка: {bet} монет.", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('mine_'))
def mine_callback(call):
    _, cell, bet = call.data.split('_')
    bet = int(bet)
    win = random.choice([True, False])
    if win:
        reward = bet * 2
        update_balance(call.from_user.id, reward)
        bot.edit_message_text(f"💣 Клетка #{cell}\n💎 АЛМАЗ! +{reward} монет!", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text(f"💣 Клетка #{cell}\n💥 БУХ! Мина!", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == '📋 Паспорт')
def passport_menu(message):
    target_user = message.from_user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user

    user = get_user(target_user.id, target_user.username or '')
    uname = f"@{target_user.username}" if target_user.username else "Нет юзернейма"

    bio = target_user.first_name.lower()
    if target_user.username:
        bio += " " + target_user.username.lower()

    found_tags = [t for t in REQUIRED_TAGS if t in bio]
    status = f"✅ Проверен ({', '.join(found_tags)})" if found_tags else "❌ Нет приписки"

    text = (f"📋 <b>ПАСПОРТ ИГРОКА</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Имя: {target_user.first_name}\n"
            f"🔗 Юзер: {uname}\n"
            f"🆔 ID: <code>{target_user.id}</code>\n"
            f"💰 Монеты: <code>{user[2]}</code>\n"
            f"🐷 Свиньи: <code>{user[3]}</code>\n"
            f"📌 Статус: {status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━")
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '⭐ VIP за звезды')
def buy_vip_stars(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⭐ Оплатить 25 Telegram Stars", callback_data="pay_vip_stars"))
    bot.send_message(message.chat.id, "👑 <b>Покупка VIP-статуса (на 1 месяц)</b>\nСтоимость: <b>25 ⭐</b>", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "pay_vip_stars")
def process_star_payment(call):
    prices = [types.LabeledPrice(label="VIP статус (1 месяц)", amount=25)]
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title="👑 VIP Статус",
        description="Премиум-статус на 1 месяц",
        invoice_payload="vip_stars",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    bot.answer_callback_query(call.id)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    set_vip_status(message.from_user.id, days=30)
    bot.send_message(message.chat.id, "🎉 <b>Оплата прошла успешно! VIP-статус выдан на 1 месяц!</b>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ['📤 Слив', '📤 Предложить слив'])
def propose_slip(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('❌ Отмена')
    msg = bot.send_message(message.chat.id, "📤 Отправь следующим сообщением контент для слива (текст, фото, видео):", reply_markup=markup)
    bot.register_next_step_handler(msg, forward_to_admin)

def forward_to_admin(message):
    if message.text == '❌ Отмена':
        bot.send_message(message.chat.id, "❌ Отменено.", reply_markup=get_main_keyboard())
        return

    user_id = message.from_user.id
    uname = f"@{message.from_user.username}" if message.from_user.username else "нет"
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Принять", callback_data=f"publish_{user_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
    )

    try:
        bot.send_message(ADMIN_CHAT_ID, f"📥 Предложка от игрока ID: <code>{user_id}</code> ({uname}):", parse_mode='HTML')
        bot.send_copy(ADMIN_CHAT_ID, message, reply_markup=markup)
        bot.send_message(message.chat.id, "✅ Отправлено на проверку администратору!", reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка отправки: {e}", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('publish_') or call.data.startswith('reject_'))
def admin_slip_handler(call):
    data = call.data.split('_')
    action = data[0]
    user_id = int(data[1])

    if action == 'publish':
        try:
            bot.send_copy(CHANNEL_ID, call.message)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, "✅ Опубликовано в канал!")
            bot.send_message(user_id, "🎉 Твой слив был успешно принят и опубликован в канале!")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка: {e}", show_alert=True)
    elif action == 'reject':
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, "❌ Предложка отклонена.")
            bot.send_message(user_id, "❌ К сожалению, твой слив был отклонен администратором.")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка: {e}", show_alert=True)

    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Монеты", callback_data="adm_coins"),
        types.InlineKeyboardButton("🐷 Свиньи", callback_data="adm_pigs"),
        types.InlineKeyboardButton("👑 Выдать VIP (30 дней)", callback_data="adm_vip")
    )
    bot.send_message(message.chat.id, "👑 <b>Админ-панель:</b>", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["adm_coins", "adm_pigs", "adm_vip"])
def adm_action_step(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    action = call.data
    if action == "adm_vip":
        msg = bot.send_message(call.message.chat.id, "✍️ Введи ID игрока для выдачи VIP на 30 дней:\n<code>ID</code>", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_add_vip)
    else:
        msg = bot.send_message(call.message.chat.id, "✍️ Введи ID и количество через пробел:\n<code>ID сумма</code>", parse_mode='HTML')
        if action == "adm_coins":
            bot.register_next_step_handler(msg, process_add_coins)
        else:
            bot.register_next_step_handler(msg, process_add_pigs)
    bot.answer_callback_query(call.id)

def process_add_coins(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        target_id, amount = int(args[0]), int(args[1])
        update_balance(target_id, amount)
        bot.send_message(message.chat.id, f"✅ Начислено {amount} монет игроку <code>{target_id}</code>!", parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

def process_add_pigs(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        target_id, amount = int(args[0]), int(args[1])
        update_pigs(target_id, amount)
        bot.send_message(message.chat.id, f"✅ Добавлено {amount} свиней игроку <code>{target_id}</code>!", parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

def process_add_vip(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        target_id = int(message.text.strip())
        set_vip_status(target_id, days=30)
        bot.send_message(message.chat.id, f"✅ VIP-статус на 30 дней успешно выдан игроку <code>{target_id}</code>!", parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

if __name__ == "__main__":
    init_db()
    print("Бот запущен со всеми исправлениями!")
    bot.infinity_polling()

