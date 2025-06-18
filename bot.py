import telebot
from telebot import types
import os
from texts import texts
from database import init_db, save_application, update_application_status, export_applications_to_csv

# Получение переменных окружения из Render
TOKEN = os.environ.get("TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID"))

bot = telebot.TeleBot(TOKEN)
user_data = {}
submitted_forms = {}  # Хранение user_id по заявкам

# Инициализация базы данных
init_db()

# Языковой хелпер
def t(chat_id, key):
    lang = user_data.get(chat_id, {}).get('lang', 'uz')
    return texts[key][lang]

# === /start ===
@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("\U0001F1FA\U0001F1FF O'zbekcha"), types.KeyboardButton("\U0001F1F7\U0001F1FA Русский"))
    welcome_text = (
        "\U0001F389 Sogʻlom Hayot loyihasiga xush kelibsiz!\n"
        "Добро пожаловать в проект «Sogʻlom Hayot»!\n\n"
        "Iltimos, tilni tanlang:\nПожалуйста, выберите язык:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
    user_data[message.chat.id] = {}
    bot.register_next_step_handler(message, set_language)

def set_language(message):
    lang = "uz" if "uz" in message.text.lower() else "ru"
    user_data[message.chat.id]['lang'] = lang
    show_main_menu(message.chat.id)

def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton(t(chat_id, "menu_submit")),
        types.KeyboardButton(t(chat_id, "menu_info")),
        types.KeyboardButton(t(chat_id, "menu_contact"))
    )
    bot.send_message(chat_id, t(chat_id, "menu_main"), reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [
    texts['menu_submit']['uz'], texts['menu_submit']['ru']])
def start_application(message):
    ask_name(message)
# === Анкета ===
def ask_name(message):
    msg = bot.send_message(message.chat.id, t(message.chat.id, "ask_name"))
    bot.register_next_step_handler(msg, ask_age)

def ask_age(message):
    user_data[message.chat.id]['name'] = message.text
    msg = bot.send_message(message.chat.id, t(message.chat.id, "ask_age"))
    bot.register_next_step_handler(msg, validate_age)

def validate_age(message):
    try:
        age = int(message.text)
        if not (6 <= age <= 12):
            bot.send_message(message.chat.id, t(message.chat.id, "age_invalid"))
            return
        user_data[message.chat.id]['age'] = age
        ask_city(message)
    except:
        bot.send_message(message.chat.id, t(message.chat.id, "ask_age"))
        ask_age(message)

def ask_city(message):
    msg = bot.send_message(message.chat.id, t(message.chat.id, "ask_city"))
    bot.register_next_step_handler(msg, save_city)

def save_city(message):
    user_data[message.chat.id]['city'] = message.text
    ask_phone(message)

def ask_phone(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton(t(message.chat.id, "ask_phone"), request_contact=True))
    bot.send_message(message.chat.id, t(message.chat.id, "ask_phone"), reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def get_contact(message):
    user_data[message.chat.id]['phone'] = message.contact.phone_number
    ask_finance(message)

def ask_finance(message):
    msg = bot.send_message(message.chat.id, t(message.chat.id, "ask_finance"))
    bot.register_next_step_handler(msg, ask_problems)

def ask_problems(message):
    user_data[message.chat.id]['finance'] = message.text
    msg = bot.send_message(message.chat.id, t(message.chat.id, "ask_problems"))
    bot.register_next_step_handler(msg, ask_photos)

def ask_photos(message):
    user_data[message.chat.id]['problems'] = message.text
    user_data[message.chat.id]['photos'] = []
    user_data[message.chat.id]['photo_step'] = 0
    ask_next_photo(message)

def ask_next_photo(message):
    step = user_data[message.chat.id]['photo_step']
    photo_dir = os.path.join(os.path.dirname(__file__), 'examples')

    captions = [
        t(message.chat.id, "photo1_caption"),
        t(message.chat.id, "photo2_caption"),
        t(message.chat.id, "photo3_caption"),
        t(message.chat.id, "photo4_caption")
    ]

    filenames = [
        '1_front.jpg',
        '2_profile.jpg',
        '3_smile.jpg',
        '4_upper_arch.jpg'
    ]

    if step < 4:
        with open(os.path.join(photo_dir, filenames[step]), 'rb') as photo_file:
            bot.send_photo(message.chat.id, photo=photo_file, caption=captions[step])
        bot.register_next_step_handler(message, collect_single_photo)
    else:
        finish_submission(message)

def collect_single_photo(message):
    if message.content_type != 'photo':
        bot.send_message(message.chat.id, t(message.chat.id, "not_photo"))
        bot.register_next_step_handler(message, collect_single_photo)
        return

    photo_id = message.photo[-1].file_id
    user_data[message.chat.id]['photos'].append(photo_id)
    user_data[message.chat.id]['photo_step'] += 1
    ask_next_photo(message)

def finish_submission(message):
    bot.send_message(message.chat.id, t(message.chat.id, "thank_you"))
    data = user_data[message.chat.id]
    submitted_forms[message.chat.id] = user_data[message.chat.id]

    save_application(data, message.chat.id, message.from_user.username or '')

    text = (
        f"\U0001F195 Yangi ariza / Новая заявка:\n"
        f"\U0001F476 Ism / Имя: {data['name']}\n"
        f"\U0001F4C5 Yosh / Возраст: {data['age']}\n"
        f"\U0001F3D9 Shahar / Город: {data['city']}\n"
        f"\U0001F4DE Telefon: {data['phone']}\n"
        f"\U0001F4B0 Holat / Финансы: {data['finance']}\n"
        f"\U0001F50D Muammolar / Жалобы: {data['problems']}\n"
        f"\U0001F464 Username: @{message.from_user.username or 'yo‘q / нет'}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("\u2705 Odoblash / Одобрить", callback_data=f"approve_{message.chat.id}"),
        types.InlineKeyboardButton("\u274C Rad etish / Отклонить", callback_data=f"reject_{message.chat.id}")
    )
    bot.send_message(ADMIN_CHAT_ID, text, reply_markup=markup)
    for p in data['photos']:
        bot.send_photo(ADMIN_CHAT_ID, p)
    show_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: message.text in [
    texts['menu_info']['uz'], texts['menu_info']['ru']])
def send_info(message):
    bot.send_message(message.chat.id, t(message.chat.id, "about_info"), parse_mode='Markdown')
    bot.send_message(message.chat.id, t(message.chat.id, "info_octa"), parse_mode='Markdown')
    show_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: message.text in [
    texts['menu_contact']['uz'], texts['menu_contact']['ru']])
def send_contacts(message):
    bot.send_message(message.chat.id, t(message.chat.id, "contact_info"), parse_mode="HTML", disable_web_page_preview=True)
    show_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_admin_decision(call):
    print(f"\U0001F4E5 Callback received: {call.data}")
    try:
        action, user_id_str = call.data.split("_", 1)
        user_id = int(user_id_str)
        lang = submitted_forms.get(user_id, {}).get('lang', 'uz')
        templates = texts['admin_reply_templates'][lang]

        if action == "approve":
            update_application_status(user_id, 'approved')
            bot.send_message(user_id, templates[0])
            bot.answer_callback_query(call.id, "\u2705 Odoblandi")
        elif action == "reject":
            update_application_status(user_id, 'rejected')
            bot.send_message(user_id, templates[1])
            bot.answer_callback_query(call.id, "\u274C Rad etildi")
    except Exception as e:
        bot.answer_callback_query(call.id, "\u26A0\uFE0F Xatolik")
        print(f"❗️ Ошибка отправки сообщения пользователю: {e}")

@bot.message_handler(commands=['export'])
def export_csv(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    filename = export_applications_to_csv()
    with open(filename, 'rb') as f:
        bot.send_document(ADMIN_CHAT_ID, f)

bot.polling(none_stop=True)
