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

bot = telebot.TeleBot(TOKEN)

# --- БАЗОВЫЕ ФУНКЦИИ (База, Баланс, VIP) ---
def init_db():
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users
                   (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 1000, 
                    is_vip INTEGER DEFAULT 0, vip_expire INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cur.fetchone()
    now = int(time.time())
    if not user:
        cur.execute("INSERT INTO users (user_id, balance, is_vip, vip_expire) VALUES (?, 1000, 0, 0)", (user_id,))
        conn.commit()
        return (user_id, 1000, 0, 0)
    # Авто-снятие VIP
    if user[2] == 1 and user[3] > 0 and now > user[3]:
        cur.execute("UPDATE users SET is_vip = 0, vip_expire = 0 WHERE user_id=?", (user_id,))
        conn.commit()
        return (user_id, user[1], 0, 0)
    return user

def update_balance(user_id, amount):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

# --- КЛАВИАТУРЫ ДЛЯ ЛС ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🎰 Казино', '📋 Паспорт', '⭐ VIP', '📤 Слив')
    return markup

# --- ОБРАБОТЧИКИ КОМАНД (Для всего) ---
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == 'private':
        bot.send_message(message.chat.id, "👋 Привет! Используй кнопки:", reply_markup=get_main_keyboard())
    else:
        bot.send_message(message.chat.id, "🎰 Игровой бот активен. Команды: /б, /п, /паспорт, /к")

@bot.message_handler(commands=['б'])
def balance_cmd(message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    user = get_user(target.id)
    text = f"👤 Игрок: {target.first_name}\n💰 Баланс: {user[1]}\n👑 VIP: {'Да' if user[2] else 'Нет'}"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['п'])
def transfer_cmd(message):
    if not message.reply_to_message: return
    try:
        amount = int(message.text.split()[1])
        sender_id = message.from_user.id
        receiver_id = message.reply_to_message.from_user.id
        if sender_id == receiver_id: return

        sender = get_user(sender_id)
        if sender[1] >= amount:
            comm = int(amount * 0.1)
            update_balance(sender_id, -amount)
            update_balance(receiver_id, amount - comm)
            update_balance(ADMIN_IDS[0], comm)
            bot.send_message(message.chat.id, f"✅ Переведено {amount-comm} (комиссия {comm})")
    except: pass

# --- ЛОГИКА ДЛЯ ЛС (КНОПКИ) ---
@bot.message_handler(func=lambda m: m.text == '🎰 Казино' and m.chat.type == 'private')
def ls_casino(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎲 Кости", callback_data="game_dice"))
    bot.send_message(message.chat.id, "Выбирай игру:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '📤 Слив' and m.chat.type == 'private')
def ls_slip(message):
    msg = bot.send_message(message.chat.id, "Пришли фото/текст для слива:")
    bot.register_next_step_handler(msg, process_slip_ls)

def process_slip_ls(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Принять", callback_data=f"pub_{message.from_user.id}"))
    bot.send_message(ADMIN_CHAT_ID, f"📥 Слив от {message.from_user.first_name}:")
    message.send_copy(ADMIN_CHAT_ID, reply_markup=markup)
    bot.send_message(message.chat.id, "✅ Отправлено админам!")

# --- ОБРАБОТКА CALLBACK ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('pub_'))
def admin_callback(call):
    user_id = int(call.data.split('_')[1])
    call.message.send_copy(CHANNEL_ID)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(user_id, "🎉 Слив принят!")

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()

