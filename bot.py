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

@bot.message_handler(commands=['start'])
def start(message):
    get_user(message.from_user.id, message.from_user.username or '')
    text = (
        "🎰 <b>Игровой бот запущен!</b>\n\n"
        "📋 <b>Команды:</b>\n"
        "• /б — Твой баланс и профиль (можно в ответ на чужое сообщение)\n"
        "• /п [сумма] — Перевод монет (в ответ на сообщение игрока, комиссия 10%)\n"
        "• /паспорт — Паспорт игрока\n"
        "• /к — Игры казино (кости, слоты, мины)\n"
        "• /слив — Предложить слив (ответь этой командой на фото/текст)"
    )
    bot.send_message(message.chat.id, text, parse_mode='HTML')

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

    text = (f"💳 <b>Профиль игрока:</b>\n"
            f"👤 Имя: {target_user.first_name}\n"
            f"🔗 Юзер: {uname}\n"
            f"🆔 ID: <code>{target_user.id}</code>\n"
            f"💰 Монеты: <code>{user[2]}</code>\n"
            f"👑 VIP статус: {vip}")
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['п'])
def transfer_coins(message):
    if not message.reply_to_message:
        bot.send_message(message.chat.id, "❌ Ответь этой командой на сообщение игрока! Пример: <code>/п 500</code>", parse_mode='HTML')
        return

    try:
        args = message.text.split()
        amount = int(args[1])
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "❌ Укажи сумму! Пример: <code>/п 500</code>", parse_mode='HTML')
        return

    if amount <= 0:
        bot.send_message(message.chat.id, "❌ Сумма должна быть больше нуля!")
        return

    sender_id = message.from_user.id
    receiver_id = message.reply_to_message.from_user.id

    if sender_id == receiver_id:
        bot.send_message(message.chat.id, "❌ Самому себе переводить нельзя!")
        return

    sender = get_user(sender_id, message.from_user.username or '')
    if sender[2] < amount:
        bot.send_message(message.chat.id, "❌ Недостаточно монет!")
        return

    get_user(receiver_id, message.reply_to_message.from_user.username or '')

    # Комиссия 10% владельцу (админу)
    commission = int(amount * 0.1)
    receiver_amount = amount - commission

    update_balance(sender_id, -amount)
    update_balance(receiver_id, receiver_amount)

    if ADMIN_IDS:
        get_user(ADMIN_IDS[0])
        update_balance(ADMIN_IDS[0], commission)

    bot.send_message(message.chat.id, f"✅ Успешно переведено <code>{receiver_amount}</code> монет (комиссия системы: {commission})!", parse_mode='HTML')

@bot.message_handler(commands=['паспорт'])
def passport_command(message):
    target_user = message.from_user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user

    user = get_user(target_user.id, target_user.username or '')
    uname = f"@{target_user.username}" if target_user.username else "Нет юзернейма"

    now = int(time.time())
    is_active_vip = user[4] == 1 and (user[5] == 0 or user[5] > now)
    if is_active_vip:
        if user[5] > 0:
            expire_date = time.strftime('%d.%m.%Y в %H:%M', time.localtime(user[5]))
            vip_text = f"👑 Да (до {expire_date})"
        else:
            vip_text = "👑 Да (бессрочно)"
    else:
        vip_text = "❌ Нет"

    text = (f"📋 <b>ПАСПОРТ ИГРОКА</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Имя: {target_user.first_name}\n"
            f"🔗 Юзер: {uname}\n"
            f"🆔 ID: <code>{target_user.id}</code>\n"
            f"💰 Монеты: <code>{user[2]}</code>\n"
            f"👑 VIP статус: {vip_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━")
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['к', 'casino'])
def casino_command(message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🎲 Кости", callback_data="game_dice"),
        types.InlineKeyboardButton("🎰 Слоты", callback_data="game_slots"),
        types.InlineKeyboardButton("💣 Мины", callback_data="game_mines")
    )
    bot.send_message(message.chat.id, "🎰 <b>Казино:</b> Выбирай игру кнопкой ниже:", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('game_'))
def casino_inline_games(call):
    user_id = call.from_user.id
    action = call.data.split('_')[1]
    user = get_user(user_id, call.from_user.username or '')

    if action == 'dice':
        bet = 50
        if user[2] < bet:
            bot.answer_callback_query(call.id, "❌ Недостаточно монет (нужно 50)!", show_alert=True)
            return
        update_balance(user_id, -bet)
        res = random.randint(1, 6)
        if res >= 4:
            win = bet * 2
            update_balance(user_id, win)
            bot.edit_message_text(f"🎲 Кости: выпало {res}\n🎉 Победа! +{win} монет!", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text(f"🎲 Кости: выпало {res}\n😢 Проигрыш! -{bet} монет", call.message.chat.id, call.message.message_id)

    elif action == 'slots':
        bet = 100
        if user[2] < bet:
            bot.answer_callback_query(call.id, "❌ Недостаточно монет (нужно 100)!", show_alert=True)
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
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

    elif action == 'mines':
        bet = 200
        if user[2] < bet:
            bot.answer_callback_query(call.id, "❌ Недостаточно монет (нужно 200)!", show_alert=True)
            return
        update_balance(user_id, -bet)
        markup = types.InlineKeyboardMarkup(row_width=3)
        for i in range(1, 10):
            markup.add(types.InlineKeyboardButton(f"📦 {i}", callback_data=f"mine_{i}_{bet}"))
        bot.edit_message_text(f"💣 <b>Мины (Квадрат 3x3)</b>\nСтавка: {bet} монет. Выбери ячейку:", call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)

    bot.answer_callback_query(call.id)

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

@bot.message_handler(commands=['vip'])
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

@bot.message_handler(commands=['слив'])
def propose_slip(message):
    if not message.reply_to_message:
        bot.send_message(message.chat.id, "❌ Ответь командой <code>/слив</code> на фото, видео или текст, который хочешь предложить!", parse_mode='HTML')
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
        message.reply_to_message.send_copy(chat_id=ADMIN_CHAT_ID, reply_markup=markup)
        bot.send_message(message.chat.id, "✅ Твой слив отправлен на проверку администратору!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка отправки: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('publish_') or call.data.startswith('reject_'))
def admin_slip_handler(call):
    data = call.data.split('_')
    action = data[0]
    user_id = int(data[1])

    if action == 'publish':
        try:
            call.message.send_copy(chat_id=CHANNEL_ID, reply_markup=None)
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
    if message.chat.type != 'private':
        bot.send_message(message.chat.id, "❌ Админ-панель доступна только в личных сообщениях с ботом!")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Монеты", callback_data="adm_coins"),
        types.InlineKeyboardButton("👑 Выдать VIP (30 дней)", callback_data="adm_vip")
    )
    bot.send_message(message.chat.id, "👑 <b>Админ-панель:</b>", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["adm_coins", "adm_vip"])
def adm_action_step(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    action = call.data
    if action == "adm_vip":
        msg = bot.send_message(call.message.chat.id, "✍️ Введи ID игрока для выдачи VIP на 30 дней:\n<code>ID</code>", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_add_vip)
    else:
        msg = bot.send_message(call.message.chat.id, "✍️ Введи ID и количество через пробел:\n<code>ID сумма</code>", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_add_coins)
    bot.answer_callback_query(call.id)

def process_add_coins(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        if not message.text:
            msg = bot.send_message(message.chat.id, "❌ Ошибка: нужно отправить текст! Введи ID и сумму еще раз:")
            bot.register_next_step_handler(msg, process_add_coins)
            return
        args = message.text.split()
        target_id, amount = int(args[0]), int(args[1])
        update_balance(target_id, amount)
        bot.send_message(message.chat.id, f"✅ Начислено {amount} монет игроку <code>{target_id}</code>!", parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка формата. Пример: <code>7959524856 1000</code>", parse_mode='HTML')

def process_add_vip(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        if not message.text:
            msg = bot.send_message(message.chat.id, "❌ Ошибка: нужно отправить текст! Введи ID игрока еще раз:")
            bot.register_next_step_handler(msg, process_add_vip)
            return
        target_id = int(message.text.strip())
        set_vip_status(target_id, days=30)
        bot.send_message(message.chat.id, f"✅ VIP-статус на 30 дней успешно выдан игроку <code>{target_id}</code>!", parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка формата. Введи только ID цифрами:", parse_mode='HTML')

if __name__ == "__main__":
    init_db()
    print("Бот успешно запущен!")
    bot.infinity_polling()

