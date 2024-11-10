import os
from pymongo import MongoClient
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = 'mongodb+srv://lightningdev722:sjW86eKb4TttfzQr@cluster0.rq0edjh.mongodb.net'
client = MongoClient(MONGO_URI)
db = client['astrobot_db']
users_collection = db['users']

# Coinbase Commerce API
COINBASE_API_KEY = '50dc4816-80be-4f1e-83b8-017a435bf302'
COINBASE_API_URL = 'https://api.commerce.coinbase.com'
def register_or_login_user(telegram_id, username=None):
    user = users_collection.find_one({'telegram_id': telegram_id})
    if not user:
        new_user = {
            'telegram_id': telegram_id,
            'username': username,
            'credits': 10
        }
        users_collection.insert_one(new_user)
        return new_user
    elif username and user.get('username') != username:
        # Update username if it has changed
        users_collection.update_one(
            {'telegram_id': telegram_id},
            {'$set': {'username': username}}
        )
        user['username'] = username
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
        {"amount": 10, "price": 1},
        {"amount": 20, "price": 1.5},
        {"amount": 50, "price": 2.5},
        {"amount": 100, "price": 4}
    ]
    return options

def create_charge(amount, price):
    """Create a new charge with Coinbase Commerce"""
    headers = {
        'X-CC-Api-Key': COINBASE_API_KEY,
        'Content-Type': 'application/json',
    }
    payload = {
        'name': f'{amount} AstroBot Credits',
        'description': f'Purchase {amount} credits for AstroBot',
        'pricing_type': 'fixed_price',
        'local_price': {
            'amount': str(price),
            'currency': 'USD'
        },
        'metadata': {
            'credit_amount': amount
        }
    }
    try:
        response = requests.post(
            f'{COINBASE_API_URL}/charges', 
            json=payload, 
            headers=headers,
            timeout=10  # Add timeout
        )
        if response.status_code == 201:
            return response.json()
        else:
            print(f"Error creating charge: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception creating charge: {str(e)}")
        return None

def get_charge_status(charge_id):
    """Get the status of a charge"""
    headers = {
        'X-CC-Api-Key': COINBASE_API_KEY,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(
            f'{COINBASE_API_URL}/charges/{charge_id}', 
            headers=headers,
            timeout=10  # Add timeout
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting charge status: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception getting charge status: {str(e)}")
        return None
