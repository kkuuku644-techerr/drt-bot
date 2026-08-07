import random
import sqlite3
import telebot
from telebot import types

TOKEN = "8935480244:AAH3w6vUIkQTnKD9eSCBL8QiwIDKF7NS4kg"
CHANNEL_ID = -1004404647295
ADMIN_CHAT_ID = -1004410094117

bot = telebot.TeleBot(TOKEN)


# ================= БАЗА ДАННЫХ =================
def init_db():
  conn = sqlite3.connect("bot.db")
  cur = conn.cursor()
  cur.execute(
      """CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 1000, is_vip INTEGER DEFAULT 0)"""
  )
  conn.commit()
  conn.close()


def get_user(user_id):
  conn = sqlite3.connect("bot.db")
  cur = conn.cursor()
  cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
  user = cur.fetchone()
  if not user:
    cur.execute(
        "INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 1000)
    )
    conn.commit()
    user = (user_id, 1000, 0)
  conn.close()
  return user


def update_balance(user_id, amount):
  conn = sqlite3.connect("bot.db")
  cur = conn.cursor()
  cur.execute(
      "UPDATE users SET balance = balance + ? WHERE user_id=?",
      (amount, user_id),
  )
  conn.commit()
  conn.close()


# ================= ГЛАВНОЕ МЕНЮ =================
@bot.message_handler(commands=["start"])
def start(message):
  get_user(message.from_user.id)
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.add("💳 Баланс", "🎲 Кости")
  markup.add("🎰 Слоты", "💣 Мины")
  markup.add("⭐ Купить VIP за звезды", "📤 Предложить слив")
  bot.send_message(
      message.chat.id,
      "🎰 <b>Главное меню:</b> Выбирай игру или действие ниже:",
      parse_mode="HTML",
      reply_markup=markup,
  )


@bot.message_handler(func=lambda m: m.text == "💳 Баланс")
def balance(message):
  user = get_user(message.from_user.id)
  vip = "👑 Да" if user[2] else "❌ Нет"
  bot.send_message(
      message.chat.id,
      f"💳 <b>Твой профиль:</b>\n💰 Баланс: {user[1]} монет\n👑 VIP статус: {vip}",
      parse_mode="HTML",
  )


# ================= ИГРЫ (РАБОТАЮТ ВЕЗДЕ) =================
@bot.message_handler(func=lambda m: m.text == "🎲 Кости")
def dice(message):
  user_id = message.from_user.id
  user = get_user(user_id)
  bet = 50
  if user[1] < bet:
    bot.send_message(message.chat.id, "❌ Недостаточно монет!")
    return
  update_balance(user_id, -bet)
  res = random.randint(1, 6)
  if res >= 4:
    win = bet * 2
    update_balance(user_id, win)
    bot.send_message(
        message.chat.id, f"🎲 Выпало: {res}\n🎉 Ты выиграл +{win} монет!"
    )
  else:
    bot.send_message(
        message.chat.id, f"🎲 Выпало: {res}\n😢 Ты проиграл -{bet} монет"
    )


@bot.message_handler(func=lambda m: m.text == "🎰 Слоты")
def slots(message):
  user_id = message.from_user.id
  user = get_user(user_id)
  bet = 100
  if user[1] < bet:
    bot.send_message(message.chat.id, "❌ Недостаточно монет!")
    return
  update_balance(user_id, -bet)
  symbols = ["🍒", "🍋", "7️⃣"]
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


@bot.message_handler(func=lambda m: m.text == "💣 Мины")
def mines(message):
  user_id = message.from_user.id
  user = get_user(user_id)
  bet = 200
  if user[1] < bet:
    bot.send_message(message.chat.id, "❌ Недостаточно монет!")
    return
  update_balance(user_id, -bet)
  markup = types.InlineKeyboardMarkup(row_width=3)
  for i in range(1, 7):
    markup.add(
        types.InlineKeyboardButton(
            f"Клетка {i}", callback_data=f"mine_{i}_{bet}"
        )
    )
  bot.send_message(
      message.chat.id,
      f"💣 <b>Мины!</b> Ставка: {bet} монет. Выбери безопасную клетку:",
      parse_mode="HTML",
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith("mine_"))
def mine_callback(call):
  _, cell, bet = call.data.split("_")
  bet = int(bet)
  win = random.choice([True, False])
  if win:
    reward = bet * 2
    update_balance(call.from_user.id, reward)
    bot.edit_message_text(
        f"💣 Клетка #{cell}\n🎉 Нашел алмаз! +{reward} монет!",
        call.message.chat.id,
        call.message.message_id,
    )
  else:
    bot.edit_message_text(
        f"💣 Клетка #{cell}\n💥 Бах! Ты подорвался на мине!",
        call.message.chat.id,
        call.message.message_id,
    )
  bot.answer_callback_query(call.id)


# ================= ПОКУПКА VIP ЗА ЗВЕЗДЫ =================
@bot.message_handler(func=lambda m: m.text == "⭐ Купить VIP за звезды")
def buy_vip_stars(message):
  markup = types.InlineKeyboardMarkup()
  markup.add(
      types.InlineKeyboardButton(
          "⭐ Оплатить 25 Telegram Stars", callback_data="pay_vip_stars"
      )
  )
  bot.send_message(
      message.chat.id,
      "👑 <b>Покупка VIP-статуса</b>\nСтоимость: <b>25 ⭐</b>",
      parse_mode="HTML",
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data == "pay_vip_stars")
def process_star_payment(call):
  prices = [types.LabeledPrice(label="VIP статус", amount=25)]
  bot.send_invoice(
      chat_id=call.message.chat.id,
      title="👑 VIP Статус",
      description="Премиум-статус",
      invoice_payload="vip_stars",
      provider_token="",
      currency="XTR",
      prices=prices,
  )
  bot.answer_callback_query(call.id)


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
  bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def got_payment(message):
  conn = sqlite3.connect("bot.db")
  cur = conn.cursor()
  cur.execute(
      "UPDATE users SET is_vip = 1 WHERE user_id=?", (message.from_user.id,)
  )
  conn.commit()
  conn.close()
  bot.send_message(
      message.chat.id, "🎉 <b>Успешно! Тебе выдан VIP-статус!</b>", parse_mode="HTML"
  )


# ================= СИСТЕМА СЛИВОВ =================
@bot.message_handler(func=lambda m: m.text == "📤 Предложить слив")
def propose_slip(message):
  bot.send_message(
      message.chat.id,
      "📤 Отправь следующим сообщением контент для модерации.",
  )
  bot.register_next_step_handler(message, forward_to_admin)


def forward_to_admin(message):
  user_id = message.from_user.id
  markup = types.InlineKeyboardMarkup()
  markup.add(
      types.InlineKeyboardButton(
          "✅ Подтвердить и слить в канал", callback_data=f"publish_{user_id}"
      )
  )
  sent = bot.forward_message(ADMIN_CHAT_ID, message.chat.id, message.message_id)
  bot.send_message(
      ADMIN_CHAT_ID,
      f"📥 Предложка от <code>{user_id}</code>:",
      parse_mode="HTML",
      reply_markup=markup,
      reply_to_message_id=sent.message_id,
  )
  bot.send_message(message.chat.id, "✅ Отправлено на проверку!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_"))
def publish_slip(call):
  try:
    bot.copy_message(
        CHANNEL_ID, call.message.chat.id, call.message.reply_to_message.message_id
    )
    bot.edit_message_text(
        "✅ Опубликовано!", call.message.chat.id, call.message.message_id
    )
  except Exception as e:
    bot.answer_callback_query(call.id, f"Ошибка: {e}", show_alert=True)
  bot.answer_callback_query(call.id)


if __name__ == "__main__":
  init_db()
  print("Бот запущен!")
  bot.infinity_polling()

