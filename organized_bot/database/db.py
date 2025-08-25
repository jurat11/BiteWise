import os
import logging
from datetime import datetime
import pytz
from google.cloud import firestore
from ..config import (
    GOOGLE_CREDENTIALS_PATH,
    USERS_COLLECTION,
    MEALS_COLLECTION,
    WATER_COLLECTION,
    STREAKS_COLLECTION
)

# Initialize Firestore
try:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH
    db = firestore.Client()
except Exception as e:
    logging.error(f"Failed to initialize Firestore: {e}")
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    db = firestore.Client()

def get_user_ref(user_id: int):
    """Get reference to user document"""
    return db.collection(USERS_COLLECTION).document(str(user_id))

def get_meals_ref(user_id: int):
    """Get reference to user's meals collection"""
    return get_user_ref(user_id).collection(MEALS_COLLECTION)

def get_water_ref(user_id: int):
    """Get reference to user's water collection"""
    return get_user_ref(user_id).collection(WATER_COLLECTION)

def get_streaks_ref(user_id: int):
    """Get reference to user's streaks collection"""
    return get_user_ref(user_id).collection(STREAKS_COLLECTION)

async def get_user_data(user_id: int) -> dict:
    """Get user data from database"""
    try:
        doc = get_user_ref(user_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logging.error(f"Error getting user data: {e}")
        return None

async def set_user_language(user_id: int, language: str):
    """Set user's preferred language"""
    try:
        get_user_ref(user_id).set({'language': language}, merge=True)
    except Exception as e:
        logging.error(f"Error setting user language: {e}")

async def log_water_intake(user_id: int, amount: int):
    """Log water intake for user"""
    try:
        water_ref = get_water_ref(user_id)
        water_ref.add({
            'amount': amount,
            'timestamp': datetime.now(pytz.UTC)
        })
        return True
    except Exception as e:
        logging.error(f"Error logging water intake: {e}")
        return False

async def log_meal(user_id: int, meal_type: str, description: str, nutrition_info: dict):
    """Log meal for user"""
    try:
        meals_ref = get_meals_ref(user_id)
        meals_ref.add({
            'type': meal_type,
            'description': description,
            'nutrition': nutrition_info,
            'timestamp': datetime.now(pytz.UTC)
        })
        return True
    except Exception as e:
        logging.error(f"Error logging meal: {e}")
        return False

async def update_user_profile(user_id: int, data: dict):
    """Update user profile data"""
    try:
        get_user_ref(user_id).set(data, merge=True)
        return True
    except Exception as e:
        logging.error(f"Error updating user profile: {e}")
        return False

async def get_today_stats(user_id: int, timezone: str = 'UTC'):
    """Get user's stats for today"""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        today_start = tz.localize(datetime.combine(now.date(), datetime.min.time())).astimezone(pytz.UTC)
        
        # Get water stats
        water_ref = get_water_ref(user_id)
        today_water = sum(w.to_dict().get('amount', 0) for w in 
                         water_ref.where('timestamp', '>=', today_start).stream())
        
        # Get meal stats
        meals_ref = get_meals_ref(user_id)
        today_meals = list(meals_ref.where('timestamp', '>=', today_start).stream())
        
        # Calculate nutrition totals
        calories = 0
        protein = 0
        carbs = 0
        fat = 0
        
        for meal in today_meals:
            meal_data = meal.to_dict()
            nutrition = meal_data.get('nutrition', {})
            calories += nutrition.get('calories', 0)
            protein += nutrition.get('protein', 0)
            carbs += nutrition.get('carbs', 0)
            fat += nutrition.get('fat', 0)
        
        return {
            'water': today_water,
            'meals_count': len(today_meals),
            'calories': calories,
            'protein': protein,
            'carbs': carbs,
            'fat': fat
        }
        
    except Exception as e:
        logging.error(f"Error getting today's stats: {e}")
        return None

async def update_streak(user_id: int, streak_type: str):
    """Update user's streak"""
    try:
        streak_ref = get_streaks_ref(user_id).document(streak_type)
        streak_doc = streak_ref.get()
        
        if streak_doc.exists:
            streak_data = streak_doc.to_dict()
            streak_data['count'] += 1
            streak_data['last_update'] = datetime.now(pytz.UTC)
        else:
            streak_data = {
                'count': 1,
                'last_update': datetime.now(pytz.UTC)
            }
            
        streak_ref.set(streak_data)
        return streak_data['count']
        
    except Exception as e:
        logging.error(f"Error updating streak: {e}")
        return None 