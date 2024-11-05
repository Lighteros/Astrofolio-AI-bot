import os
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI
from dotenv import load_dotenv
import time

from script1 import analyze_synastry_full
from script2 import analyze_synastry_partial
from script3 import analyze_synastry_basic
from script4 import analyze_natal_chart_full
from script5 import analyze_natal_chart_basic
from db_operations import (
    register_or_login_user, 
    reduce_credit, 
    get_user_credits, 
    add_credits, 
    create_purchase_options
)
# Load environment variables
load_dotenv()

# Initialize bot and OpenAI
BOT_TOKEN = '7527031210:AAGrQVzOupSX7VQK_6HuQkElgN100SmSCQ0'
OPENAI_API_KEY = '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'

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# Store user states, data, and messages
user_states = {}
user_data = {}
user_messages = {}  # Store temporary message IDs (questions, menus)
user_outputs = {}   # Store permanent message IDs (readings)

class UserState:
    IDLE = "idle"
    AWAITING_BIRTHDAY = "awaiting_birthday"
    AWAITING_TIME = "awaiting_time"
    AWAITING_LOCATION = "awaiting_location"
    AWAITING_MALE_BIRTHDAY = "awaiting_male_birthday"
    AWAITING_MALE_TIME = "awaiting_male_time"
    AWAITING_MALE_LOCATION = "awaiting_male_location"
    AWAITING_FEMALE_BIRTHDAY = "awaiting_female_birthday"
    AWAITING_FEMALE_TIME = "awaiting_female_time"
    AWAITING_FEMALE_LOCATION = "awaiting_female_location"
    AWAITING_TOKEN_SYMBOL = "awaiting_token_symbol"
    GENERATING_READING = "generating_reading"

def cleanup_temp_messages(chat_id):
    """Delete all temporary messages for a chat"""
    if chat_id in user_messages:
        for msg_id in user_messages[chat_id]:
            try:
                bot.delete_message(chat_id, msg_id)
            except:
                pass
        user_messages[chat_id] = []

def store_temp_message(chat_id, message_id):
    """Store temporary message ID"""
    if chat_id not in user_messages:
        user_messages[chat_id] = []
    user_messages[chat_id].append(message_id)

def store_output_message(chat_id, message_id):
    """Store permanent output message ID"""
    if chat_id not in user_outputs:
        user_outputs[chat_id] = []
    user_outputs[chat_id].append(message_id)

def send_temp_message(chat_id, text, reply_markup=None):
    """Send temporary message (questions, menus) and store its ID"""
    cleanup_temp_messages(chat_id)
    msg = bot.send_message(chat_id, text, reply_markup=reply_markup)
    store_temp_message(chat_id, msg.message_id)
    return msg

def send_output_message(chat_id, text, parse_mode=None):
    """Send permanent message (readings) and store its ID"""
    msg = bot.send_message(chat_id, text, parse_mode=parse_mode)
    store_output_message(chat_id, msg.message_id)
    return msg

def create_main_menu():
    """Create the main menu with reading type options"""
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("🔮 Personal Reading", callback_data="reading_personal"),
        InlineKeyboardButton("💰 Token Launch Reading", callback_data="reading_token"),
        InlineKeyboardButton("❤️ Compatibility Reading", callback_data="reading_synastry")
    )
    return markup

def parse_date_with_gpt(text):
    """Use GPT to parse date from any format"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a date parser. Convert the given date to YYYY-MM-DD format. Only return the date in YYYY-MM-DD format, nothing else. If you cannot parse the date, return 'INVALID'."},
            {"role": "user", "content": text}
        ],
        temperature=0,
        max_tokens=20
    )
    result = response.choices[0].message.content.strip()
    return result if result != "INVALID" else None

def parse_time_with_gpt(text):
    print(f"time input {text}")
    """Use GPT to parse time from any format"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a time parser. Convert the given time or text which indicates certain time span to HH:MM format (24-hour). Just return general time in HH:MM format if input is time span text(for example, morning, early night). Only return the time in HH:MM format, nothing else. If you cannot parse the time, return 'INVALID'."},
            {"role": "user", "content": text}
        ],
        temperature=0,
        max_tokens=20
    )
    result = response.choices[0].message.content.strip()
    return result if result != "INVALID" else "12:00"

from datetime import datetime

def generate_astrological_reading(data):
    """Generate astrological reading using the appropriate script and gpt-4o"""
    reading_type = data.get("type")
    
    def parse_approximate_time(time_str):
        time_map = {
            "morning": "09:00",
            "early morning": "07:00",
            "afternoon": "14:00",
            "evening": "19:00",
            "early evening": "17:00",
            "night": "22:00",
            "late night": "23:59"
        }
        return time_map.get(time_str.lower(), "12:00")  # Default to noon if not found

    if reading_type == "synastry":
        male_time = data.get('male_time', '12:00')
        female_time = data.get('female_time', '12:00')
        
        if not male_time.count(':'):
            male_time = parse_approximate_time(male_time)
        if not female_time.count(':'):
            female_time = parse_approximate_time(female_time)

        if all(key in data for key in ['male_date', 'male_location', 'female_date', 'female_location']):
            corpus = analyze_synastry_full(
                birthday1=datetime.strptime(data['male_date'], "%Y-%m-%d"),
                location1=data['male_location'],
                gender1="male",
                birthday2=datetime.strptime(data['female_date'], "%Y-%m-%d"),
                location2=data['female_location'],
                gender2="female",
                time1=datetime.strptime(male_time, "%H:%M").time(),
                time2=datetime.strptime(female_time, "%H:%M").time()
            )
            print(f"{corpus}")
        else:
            # Use partial or basic analysis if full data is not available
            if 'male_location' in data or 'female_location' in data:
                corpus = analyze_synastry_partial(
                    birthday1=datetime.strptime(data['male_date'], "%Y-%m-%d"),
                    location1=data.get('male_location', 'Unknown'),
                    gender1="male",
                    birthday2=datetime.strptime(data['female_date'], "%Y-%m-%d"),
                    location2=data.get('female_location', 'Unknown'),
                    gender2="female",
                    time1=datetime.strptime(male_time, "%H:%M").time(),
                    time2=datetime.strptime(female_time, "%H:%M").time()
                )
                print(f"{corpus}")
            else:
                corpus = analyze_synastry_basic(
                    birthday1=datetime.strptime(data['male_date'], "%Y-%m-%d"),
                    gender1="male",
                    birthday2=datetime.strptime(data['female_date'], "%Y-%m-%d"),
                    gender2="female"
                )
                print(f"{corpus}")
        
        prompt = """Give me a compatibility reading for these two people. I want it to be concise, give 1-10 ratings about various parts of their compatibility focusing on the planets that matter for each category. 1-10 ratings for personality compatibility, Romantic compatibility, sexual compatibility, friendship compatibility, communication compatibility, luck compatibility, long-term stability, and marriage compatibility (juno mostly but feel free to include other aspects you deem relevant). Go into detail on the aspects and placements that you deem important. At the end give an overall compatibility rating 1-10. But you don’t have to just do the planets I mentioned can do anything you deem relevant. Make bold guesses about their relationship even how they might have met. Give the reading the way a person who is a Capricorn with some Sagittarius blends would give the reading: very practical, but also enthusiastic when they see something good in the astrology chart or concerned when they see something bad in the chart.

        Astrological Data:
        {corpus}
        """.format(corpus=corpus)
    
    elif reading_type == "token":
        try:
            time = data.get('time', '12:00')
            if not time.count(':'):
                time = parse_approximate_time(time)

            corpus = analyze_natal_chart_basic(
                birthday=datetime.strptime(data['date'], "%Y-%m-%d")
            )
            
            if isinstance(corpus, dict) and 'placements' in corpus:
                placements = corpus['placements']
                aspects = corpus.get('aspects', [])
                corpus_text = f"Placements:\n{', '.join(placements)}\n\nAspects:\n{', '.join(aspects)}"
            else:
                corpus_text = str(corpus)
            
            print(f"Token corpus {corpus_text}")
            
            prompt = f"""This is an astrological reading for the launch date of a Token: {data.get('symbol', 'Unknown')}. You are trying to guess if it will be successful or lucky or have longevity, and what the community might be like, and how it might develop to success or failure. Also what the general vibe of the community and what the price action might be like based on its astrological personality. Give ratings 1-10 for success potential, longevity, community enthusiasm and engagement, market presence, financial management, innovation and creativity, and risk of volatility. Give the reading the way a person who is a Capricorn with some Sagittarius blends would give the reading: practical and concise but also bold.

            Astrological Data:
            {corpus_text}
            """
        except Exception as e:
            print(f"Error in token reading: {str(e)}")
            return f"Unable to generate token reading due to error: {str(e)}"
    
    else:  # personal reading
        time = data.get('time', '12:00')
        if not time.count(':'):
            time = parse_approximate_time(time)

        if 'location' in data:
            corpus = analyze_natal_chart_full(
                birthday=datetime.strptime(data['date'], "%Y-%m-%d"),
                time=datetime.strptime(time, "%H:%M").time(),
                city=data['location']
            )
            print(f"{corpus}")
        else:
            corpus = analyze_natal_chart_basic(
                birthday=datetime.strptime(data['date'], "%Y-%m-%d")
            )
            print(f"{corpus}")
        
        prompt = """Give me an individual reading for this person. I want it to be concise, give 1-10 ratings about various parts of their astrology focusing on the planets that matter for each category. 1-10 ratings for overall ease of their life rating (will it have many challenges), romantic success, wealth success, friendship success, how attractive they might be, career success and try to guess what kind of career they might be suitable for. You can try to guess about their personal values as well. At the end give an overall compatibility rating 1-10. But you don't have to just do the planets I mentioned can do anything you deem relevant. Make bold guesses about their relationship even how they might have met. Give the reading the way a person who is a Capricorn with some Sagittarius blends would give the reading: very practical and concise, but also enthusiastic when they see something good in the astrology chart or concerned when they see something bad in the chart.

        Astrological Data:
        {corpus}
        """.format(corpus=corpus)

    print(f"{prompt}")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert astrologer providing detailed readings."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content

def show_input_menu(chat_id, message_text):
    """Helper function to show menu with back button"""
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="back_to_start"))
    send_temp_message(chat_id, message_text, reply_markup=markup)

def create_optional_menu(reading_type, data):
    """Create menu for optional inputs"""
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    buttons = []
    
    if reading_type == 'synastry':
        male_has_time = "male_time" in data
        male_has_location = "male_location" in data
        female_has_time = "female_time" in data
        female_has_location = "female_location" in data
        
        if not male_has_time:
            buttons.append(InlineKeyboardButton("➕ Add His Time", callback_data="add_male_time"))
        if not male_has_location:
            buttons.append(InlineKeyboardButton("➕ Add His Location", callback_data="add_male_location"))
        if not female_has_time:
            buttons.append(InlineKeyboardButton("➕ Add Her Time", callback_data="add_female_time"))
        if not female_has_location:
            buttons.append(InlineKeyboardButton("➕ Add Her Location", callback_data="add_female_location"))
    else:
        has_time = "time" in data
        has_location = "location" in data
        
        if not has_time and reading_type != 'token':
            buttons.append(InlineKeyboardButton("➕ Add Time", callback_data="add_time"))
        if not has_location and reading_type != 'token':
            buttons.append(InlineKeyboardButton("➕ Add Location", callback_data="add_location"))

    buttons.append(InlineKeyboardButton("✨ Generate Reading", callback_data="generate"))
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i + 1])
        else:
            markup.row(buttons[i])
    
    return markup

def show_optional_inputs(chat_id):
    reading_type = user_data[chat_id]["type"]
    msg = "✨ Information received!\n\n"
    msg += "Current details:\n"
    
    if reading_type == 'synastry':
        msg += "👨 His Details:\n"
        msg += f"📅 Date: {user_data[chat_id].get('male_date')}\n"
        if 'male_time' in user_data[chat_id]:
            msg += f"⏰ Time: {user_data[chat_id]['male_time']}\n"
        if 'male_location' in user_data[chat_id]:
            msg += f"📍 Location: {user_data[chat_id]['male_location']}\n"
        
        msg += "\n👩 Her Details:\n"
        msg += f"📅 Date: {user_data[chat_id].get('female_date')}\n"
        if 'female_time' in user_data[chat_id]:
            msg += f"⏰ Time: {user_data[chat_id]['female_time']}\n"
        if 'female_location' in user_data[chat_id]:
            msg += f"📍 Location: {user_data[chat_id]['female_location']}\n"
    elif reading_type == 'token':
        msg += f"🪙 Symbol: {user_data[chat_id].get('symbol')}\n"
        msg += f"📅 Launch Date: {user_data[chat_id].get('date')}\n"
        if "time" not in user_data[chat_id]:
            user_states[chat_id] = UserState.AWAITING_TIME
            show_input_menu(chat_id, "⏰ Please enter the launch time (required)")
            return
        msg += f"⏰ Launch Time: {user_data[chat_id]['time']}\n"
    else:
        msg += f"📅 Date: {user_data[chat_id].get('date')}\n"
        if 'time' in user_data[chat_id]:
            msg += f"⏰ Time: {user_data[chat_id]['time']}\n"
        if 'location' in user_data[chat_id]:
            msg += f"📍 Location: {user_data[chat_id]['location']}\n"
    
    msg += "\nWhat would you like to do next?"
    markup = create_optional_menu(reading_type, user_data[chat_id])
    send_temp_message(chat_id, msg, reply_markup=markup)

def generate_reading(chat_id):
    """Generate and send the reading to the user"""
    try:
        # Send generating message
        credits = get_user_credits(chat_id)
        if credits <= 0:
            show_purchase_options(chat_id)
            return

        generating_msg = send_temp_message(chat_id, "🔮 Generating your reading... Please wait...")
        
        # Generate the reading
        reading = generate_astrological_reading(user_data[chat_id])

        print("f{reading}")
        
        # Delete generating message
        cleanup_temp_messages(chat_id)
        
        # Send the reading
        send_output_message(chat_id, reading, parse_mode='Markdown')
        
        # Reset state and show main menu
        user_states[chat_id] = UserState.IDLE
        user_data[chat_id] = {}
        
        welcome_msg = f"\U0001F31F Reading generated! You now have {credits} credits left. Would you like another reading?"
        send_temp_message(chat_id, welcome_msg, reply_markup=create_main_menu())
        
    except Exception as e:
        send_temp_message(chat_id, "❌ Sorry, there was an error generating your reading. Please try again.")
        print(f"Error generating reading: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_states[chat_id] = UserState.IDLE
    user_data[chat_id] = {}
    
    user = register_or_login_user(chat_id)
    credits = user['credits']
    
    welcome_msg = (f"\U0001F31F Welcome to AstroBot! \U0001F31F\n\n"
                   f"You have {credits} credits.\n\n"
                   "I can provide you with:\n"
                   "\U0001F52E Personal Astrological Reading\n"
                   "\U0001F4B0 Token Launch Reading\n"
                   "❤️ Compatibility Reading\n\n"
                   "Please select a reading type:")
    
    send_temp_message(chat_id, welcome_msg, reply_markup=create_main_menu())

# Add these new functions to handle purchases
def show_purchase_options(chat_id):
    options = create_purchase_options()
    markup = InlineKeyboardMarkup()
    for option in options:
        button_text = f"Buy {option['amount']} credits for ${option['price']}"
        callback_data = f"buy_{option['amount']}"
        markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))
    
    msg = "You've run out of credits! Please purchase more to continue:"
    send_temp_message(chat_id, msg, reply_markup=markup)

def process_purchase(chat_id, amount):
    # In a real application, you would integrate with a payment system here
    # For this example, we'll just add the credits directly
    add_credits(chat_id, amount)
    credits = get_user_credits(chat_id)
    msg = f"Purchase successful! You now have {credits} credits."
    send_temp_message(chat_id, msg, reply_markup=create_main_menu())

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    
    if call.data.startswith("buy_"):
        amount = int(call.data.split("_")[1])
        process_purchase(chat_id, amount)
    elif call.data == "back_to_start":
        # Check if we're in an optional input state
        current_state = user_states.get(chat_id)
        if current_state in [
            UserState.AWAITING_TIME, 
            UserState.AWAITING_LOCATION,
            UserState.AWAITING_MALE_TIME,
            UserState.AWAITING_MALE_LOCATION,
            UserState.AWAITING_FEMALE_TIME,
            UserState.AWAITING_FEMALE_LOCATION
        ]:
            # Return to optional inputs window
            show_optional_inputs(chat_id)
        else:
            # Return to main menu
            user_states[chat_id] = UserState.IDLE
            user_data[chat_id] = {}
            welcome_msg = ("🌟 Welcome back! 🌟\n\n"
                        "Please select a reading type:")
            send_temp_message(chat_id, welcome_msg, reply_markup=create_main_menu())
        return

    if call.data.startswith("reading_"):
        reading_type = call.data.split("_")[1]
        user_data[chat_id] = {"type": reading_type}
        
        if reading_type == "token":
            user_states[chat_id] = UserState.AWAITING_TOKEN_SYMBOL
            show_input_menu(chat_id, "🪙 Please enter the token symbol")
        elif reading_type == "synastry":
            user_states[chat_id] = UserState.AWAITING_MALE_BIRTHDAY
            show_input_menu(chat_id, "📅 Please enter his birthday (required)")
        else:
            user_states[chat_id] = UserState.AWAITING_BIRTHDAY
            show_input_menu(chat_id, "📅 Please enter your birthday (required)")

    elif call.data.startswith("add_"):
        action = call.data[4:]  # Remove 'add_' prefix
        if action == "male_time":
            user_states[chat_id] = UserState.AWAITING_MALE_TIME
            show_input_menu(chat_id, "⏰ Please enter his birth time\n\nYou can enter:\n- Exact time (e.g., 14:30)\n- Approximate time (e.g., morning, afternoon)\n- General time (e.g., early morning, late night)")
        elif action == "male_location":
            user_states[chat_id] = UserState.AWAITING_MALE_LOCATION
            show_input_menu(chat_id, "📍 Please enter his birth location")
        elif action == "female_time":
            user_states[chat_id] = UserState.AWAITING_FEMALE_TIME
            show_input_menu(chat_id, "⏰ Please enter her birth time\n\nYou can enter:\n- Exact time (e.g., 14:30)\n- Approximate time (e.g., morning, afternoon)\n- General time (e.g., early morning, late night)")
        elif action == "female_location":
            user_states[chat_id] = UserState.AWAITING_FEMALE_LOCATION
            show_input_menu(chat_id, "📍 Please enter her birth location")
        elif action == "time":
            user_states[chat_id] = UserState.AWAITING_TIME
            show_input_menu(chat_id, "⏰ Please enter the time\n\nYou can enter:\n- Exact time (e.g., 14:30)\n- Approximate time (e.g., morning, afternoon)\n- General time (e.g., early morning, late night)")
        elif action == "location":
            user_states[chat_id] = UserState.AWAITING_LOCATION
            show_input_menu(chat_id, "📍 Please enter the location")

    elif call.data == "generate":
        generate_reading(chat_id)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text
    current_state = user_states.get(chat_id, UserState.IDLE)
    
    # Try to delete user's message
    try:
        bot.delete_message(chat_id, message.message_id)
    except:
        pass

    if current_state == UserState.IDLE:
        send_temp_message(chat_id, "Please use the menu to select a reading type.", reply_markup=create_main_menu())
        return

    if current_state == UserState.AWAITING_TOKEN_SYMBOL:
        user_data[chat_id]['symbol'] = text.strip().upper()
        user_states[chat_id] = UserState.AWAITING_BIRTHDAY
        show_input_menu(chat_id, "📅 Please enter the launch date")
        return

    if current_state in [UserState.AWAITING_BIRTHDAY, UserState.AWAITING_MALE_BIRTHDAY, UserState.AWAITING_FEMALE_BIRTHDAY]:
        date = parse_date_with_gpt(text)
        if not date:
            show_input_menu(chat_id, "❌ Invalid date format. Please try again with a valid date.")
            return

        if current_state == UserState.AWAITING_BIRTHDAY:
            user_data[chat_id]['date'] = date
            show_optional_inputs(chat_id)
        elif current_state == UserState.AWAITING_MALE_BIRTHDAY:
            user_data[chat_id]['male_date'] = date
            user_states[chat_id] = UserState.AWAITING_FEMALE_BIRTHDAY
            show_input_menu(chat_id, "📅 Please enter her birthday (required)")
        elif current_state == UserState.AWAITING_FEMALE_BIRTHDAY:
            user_data[chat_id]['female_date'] = date
            show_optional_inputs(chat_id)

    elif current_state in [UserState.AWAITING_TIME, UserState.AWAITING_MALE_TIME, UserState.AWAITING_FEMALE_TIME]:
        time = parse_time_with_gpt(text)
        print(f"{time}")
        if not time and text.lower() not in ['morning', 'afternoon', 'evening', 'night']:
            show_input_menu(chat_id, "❌ Invalid time format. Please try again with a valid time.")
            return

        if current_state == UserState.AWAITING_TIME:
            user_data[chat_id]['time'] = time or text
            show_optional_inputs(chat_id)
        elif current_state == UserState.AWAITING_MALE_TIME:
            user_data[chat_id]['male_time'] = time or text
            show_optional_inputs(chat_id)
        elif current_state == UserState.AWAITING_FEMALE_TIME:
            user_data[chat_id]['female_time'] = time or text
            show_optional_inputs(chat_id)

    elif current_state in [UserState.AWAITING_LOCATION, UserState.AWAITING_MALE_LOCATION, UserState.AWAITING_FEMALE_LOCATION]:
        if current_state == UserState.AWAITING_LOCATION:
            user_data[chat_id]['location'] = text
        elif current_state == UserState.AWAITING_MALE_LOCATION:
            user_data[chat_id]['male_location'] = text
        elif current_state == UserState.AWAITING_FEMALE_LOCATION:
            user_data[chat_id]['female_location'] = text
        
        show_optional_inputs(chat_id)

def main():
    """Main function to start the bot"""
    print("Starting bot...")
    bot.infinity_polling()

if __name__ == "__main__":
    main()