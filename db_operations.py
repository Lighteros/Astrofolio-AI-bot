import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = 'mongodb+srv://lightningdev722:sjW86eKb4TttfzQr@cluster0.rq0edjh.mongodb.net'
client = MongoClient(MONGO_URI)
db = client['astrobot_db']
users_collection = db['users']

def register_or_login_user(telegram_id):
    user = users_collection.find_one({'telegram_id': telegram_id})
    if not user:
        new_user = {
            'telegram_id': telegram_id,
            'credits': 10
        }
        users_collection.insert_one(new_user)
        return new_user
    return user

def reduce_credit(telegram_id):
    users_collection.update_one(
        {'telegram_id': telegram_id},
        {'$inc': {'credits': -1}}
    )

def get_user_credits(telegram_id):
    user = users_collection.find_one({'telegram_id': telegram_id})
    return user['credits'] if user else 0

def add_credits(telegram_id, amount):
    users_collection.update_one(
        {'telegram_id': telegram_id},
        {'$inc': {'credits': amount}}
    )

def create_purchase_options():
    options = [
        {"amount": 10, "price": 5},
        {"amount": 20, "price": 9},
        {"amount": 50, "price": 20},
        {"amount": 100, "price": 35}
    ]
    return options
