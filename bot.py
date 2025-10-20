import telebot
import requests
import time
import threading
import logging
import schedule
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# -------- CONFIG --------
BOT_TOKEN = "7523032874:AAHmefM434Upk0_Rf7djBCo7HCG6hQwpDJU"
ALLOWED_GROUP_ID = -1002147041893  # Your allowed group ID
VIP_USERS = {5159972988}

# APIs - separate URLs
LIKE_API_URL = "https://download-lwqf.vercel.app/like?uid={uid}&server_name={region}&key=gst"     # Replace with your like API
VISIT_API_URL = "https://visitor-n8h7.vercel.app/{region}/{uid}"   # Replace with your visit API

# -------- SETUP --------
bot = telebot.TeleBot(BOT_TOKEN)

like_request_tracker = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# -------- DAILY RESET --------
def reset_daily_limits():
    global like_request_tracker
    like_request_tracker = {}
    logging.info("Daily request limits reset.")

schedule.every().day.at("00:00").do(reset_daily_limits)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_schedule, daemon=True).start()

# -------- LIKE BOT FUNCTIONS --------
def call_like_api(region, uid):
    url = LIKE_API_URL.format(uid=uid, region=region)
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200 or not response.text.strip():
            logging.error(f"Like API response error: Status {response.status_code}")
            return "API_ERROR"
        return response.json()
    except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError) as e:
        logging.error(f"Like API exception: {e}")
        return "API_ERROR"

def process_like(message, region, uid):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if user_id not in VIP_USERS and like_request_tracker.get(user_id, False):
        bot.reply_to(message, "⚠️ You have exceeded your daily request limit! ⏳ Try again later.")
        return

    progress_stages = [
        ("⏳ Starting like request...", 0),
        ("🔄 Fetching like data...", 25),
        ("🔍 Validating UID & Region...", 50),
        ("👍 Sending like request...", 75),
        ("✅ Like process almost done...", 90)
    ]

    progress_msg = bot.reply_to(message, f"{progress_stages[0][0]} {progress_stages[0][1]}% {'░' * 10}")

    for stage, percent in progress_stages[1:]:
        time.sleep(1)
        bars_filled = percent // 10
        bars_empty = 10 - bars_filled
        progress_bar = "▓" * bars_filled + "░" * bars_empty
        try:
            bot.edit_message_text(f"{stage} {percent}% {progress_bar}", chat_id, progress_msg.message_id)
        except Exception as e:
            logging.error(f"Failed to edit message: {e}")

    response = call_like_api(region, uid)

    if response == "API_ERROR":
        bot.edit_message_text("🚨 Like API ERROR! ⚒️ Please wait for some time.", chat_id, progress_msg.message_id)
        return

    if response.get("status") == 1:
        if user_id not in VIP_USERS:
            like_request_tracker[user_id] = True  # Mark usage

        try:
            photos = bot.get_user_profile_photos(user_id)
            if photos.total_count > 0:
                file_id = photos.photos[0][-1].file_id
                markup = InlineKeyboardMarkup()
                share_button = InlineKeyboardButton("Share Bot", url="https://t.me/hiladu_bot")
                markup.add(share_button)

                bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=progress_msg.message_id,
                    media=telebot.types.InputMediaPhoto(
                        file_id,
                        caption=(
                            f"✅ **Like Added Successfully!**\n"
                            f"🔹 **UID:** `{response.get('UID', 'N/A')}`\n"
                            f"🔸 **Player Nickname:** `{response.get('PlayerNickname', 'N/A')}`\n"
                            f"🔸 **Likes Before:** `{response.get('LikesbeforeCommand', 'N/A')}`\n"
                            f"🔸 **Likes After:** `{response.get('LikesafterCommand', 'N/A')}`\n"
                            f"🔸 **Likes By Bot:** `{response.get('LikesGivenByAPI', 'N/A')}`\n\n"
                            "🗿 **SHARE US FOR MORE:**"
                        ),
                        parse_mode="Markdown"
                    ),
                    reply_markup=markup
                )
                return
        except Exception as e:
            logging.error(f"Error sending photo media: {e}")

        markup = InlineKeyboardMarkup()
        share_button = InlineKeyboardButton("Share Bot", url="https://t.me/hiladu_bot")
        markup.add(share_button)

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=progress_msg.message_id,
            text=(
                f"✅ **Like Added Successfully!**\n"
                f"🔹 **UID:** `{response.get('UID', 'N/A')}`\n"
                f"🔸 **Player Nickname:** `{response.get('PlayerNickname', 'N/A')}`\n"
                f"🔸 **Likes Before:** `{response.get('LikesbeforeCommand', 'N/A')}`\n"
                f"🔸 **Likes After:** `{response.get('LikesafterCommand', 'N/A')}`\n"
                f"🔸 **Likes By Bot:** `{response.get('LikesGivenByAPI', 'N/A')}`\n\n"
                "🗿 **SHARE US FOR MORE:**"
            ),
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=progress_msg.message_id,
            text=(
                f"💔 UID `{uid}` has already received Max Likes for Today 💔.\n"
                "🔄 Please Try a different UID."
            ),
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['like'])
def handle_like(message):
    if message.chat.id != ALLOWED_GROUP_ID:
        bot.reply_to(message, "🚫 This group is not allowed to use this bot! ❌")
        return

    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "❌ Incorrect format! Use: `/like {region} {uid}`\n📌 Example: `/like ind 8385763215`", parse_mode="Markdown")
        return

    region, uid = args[1], args[2]

    if not region.isalpha() or not uid.isdigit():
        bot.reply_to(message, "⚠️ Invalid input! Region should be text and UID should be numbers.\n📌 Example: `/like ind 8385763215`")
        return

    threading.Thread(target=process_like, args=(message, region, uid)).start()

# -------- VISIT BOT FUNCTIONS --------

def call_visit_api(region, uid):
    url = VISIT_API_URL.format(uid=uid, region=region)
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200 or "application/json" not in response.headers.get("Content-Type", ""):
            logging.error(f"Visit API response error: Status {response.status_code} or invalid content type")
            return None
        return response.json()
    except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError) as e:
        logging.error(f"Visit API exception: {e}")
        return None

@bot.message_handler(commands=['visit'])
def handle_visit(message):
    if message.chat.id != ALLOWED_GROUP_ID:
        return  # Ignore if not in allowed group

    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ Wrong format!\n✅ Use: <code>/visit IND 1640556162</code>",
            parse_mode="HTML"
        )
        return

    region = args[1].strip()
    uid = args[2].strip()

    wait_msg = bot.reply_to(message, "⏳ <b>Processing your visit request...</b>", parse_mode="HTML")

    data = call_visit_api(region, uid)

    if data is None:
        bot.edit_message_text(
            "⚠️ API request failed or returned invalid response.",
            chat_id=message.chat.id,
            message_id=wait_msg.message_id,
            parse_mode="HTML"
        )
        return

    if data.get("fail") == 0:
        reply_text = (
            "╭─────────────────────⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡─────────────────────╮\n"
            "┃                    🌌 𝗚𝗔𝗠𝗘𝗥 𝗣𝗥𝗢𝗙𝗜𝗟𝗘 𝗥𝗘𝗣𝗢𝗥𝗧                   ┃\n"
            "╰─────────────────────⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡─────────────────────╯\n\n"
            f"🎮 <b>Name</b>       : <code>{data.get('nickname')}</code>\n"
            f"🆔 <b>UID</b>        : <code>{data.get('uid')}</code>\n"
            f"🌍 <b>Region</b>     : <b>{data.get('region')}</b>\n"
            f"📶 <b>Level</b>      : <b>{data.get('level')}</b>\n"
            f"💖 <b>Likes</b>      : <b>{data.get('likes')}</b>\n"
            f"📩 <b>Visit Status</b> : ✅ <b>{data.get('success')}</b>    ❌ <b>{data.get('fail')}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏷 <i>Generated securely by</i> <b>@Bishal_puku</b>"
        )
    else:
        reply_text = "❌ Visit Failed. Please check your UID or Region."

    bot.edit_message_text(
        reply_text,
        chat_id=message.chat.id,
        message_id=wait_msg.message_id,
        parse_mode="HTML"
    )

# -------- HELP COMMAND --------
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "🤖 *Bot Commands Help*\n\n"
        "/like {region} {uid} - Send like request.\n"
        "Example: `/like ind 8385763215`\n\n"
        "/visit {region} {uid} - Send visit request.\n"
        "Example: `/visit ind 1640556162`\n\n"
        "Only allowed in the designated group.\n"
        "Daily limit applies for non-VIP users.\n"
        "For support, contact admin."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

# -------- START COMMAND WITH BUTTONS --------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    keyboard = InlineKeyboardMarkup()
    start_button = InlineKeyboardButton("Show Commands", callback_data="show_commands")
    keyboard.add(start_button)
    welcome_text = (
        "👋 Welcome! I am your Game Like & Visit Bot.\n"
        "Click the button below to see all available commands."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "show_commands")
def show_commands(call):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("/like", callback_data="cmd_like"),
        InlineKeyboardButton("/visit", callback_data="cmd_visit"),
        InlineKeyboardButton("/help", callback_data="cmd_help")
    )
    bot.edit_message_text(
        "Choose a command to use:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("cmd_"))
def handle_command_buttons(call):
    cmd = call.data.split("_")[1]
    chat_id = call.message.chat.id
    if cmd == "like":
        bot.send_message(chat_id, "To send likes, use:\n/like {region} {uid}\nExample: /like ind 8385763215")
    elif cmd == "visit":
        bot.send_message(chat_id, "To send visits, use:\n/visit {region} {uid}\nExample: /visit ind 1640556162")
    elif cmd == "help":
        send_help(call.message)
    bot.answer_callback_query(call.id)

# -------- RUN BOT --------
bot.polling(none_stop=True)
