import os
from google.cloud import firestore
from datetime import datetime
import pytz
from tabulate import tabulate
from collections import Counter, defaultdict
import csv

# Configuration
GOOGLE_CREDENTIALS_PATH = "./credentials/sturdy-lead-454406-n3-16c47cb3a35a.json"
# Set Google Cloud credentials environment variable
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH

# Define Uzbekistan timezone
UZB_TZ = pytz.timezone('Asia/Tashkent')

try:
    db = firestore.Client()
except Exception as e:
    print(f"Failed to initialize Firestore: {e}")
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    db = firestore.Client()

def get_user_stats():
    """Retrieve and display comprehensive user statistics"""
    users_ref = db.collection('users')
    users = list(users_ref.stream())
    
    total_users = len(users)
    if total_users == 0:
        print("No users found in the database.")
        return

    # Initialize counters and aggregators
    languages = Counter()
    goals = Counter()
    total_meals = 0
    total_water = 0
    active_users_24h = 0
    active_users_7d = 0
    gender_count = Counter()
    age_ranges = Counter()
    activity_levels = Counter()
    
    # Time thresholds
    now = datetime.now(pytz.utc)
    last_24h = now.timestamp() - (24 * 3600)
    last_7d = now.timestamp() - (7 * 24 * 3600)

    # User data storage
    user_data_list = [] # Renamed to avoid conflict with user_data dict in main bot
    all_users_for_sorting = []
    
    for user in users:
        data = user.to_dict()
        all_users_for_sorting.append(data) # Store raw data for sorting
        
        # Basic user info
        languages[data.get('language', 'unknown')] += 1
        goals[data.get('goal', 'unknown')] += 1
        gender_count[data.get('gender', 'unknown')] += 1
        activity_levels[data.get('activity_level', 'unknown')] += 1
        
        # Age ranges
        age = data.get('age', 0)
        if age < 18:
            age_ranges['<18'] += 1
        elif age < 25:
            age_ranges['18-24'] += 1
        elif age < 35:
            age_ranges['25-34'] += 1
        elif age < 50:
            age_ranges['35-49'] += 1
        else:
            age_ranges['50+'] += 1

        # Activity check
        last_active = data.get('last_active')
        if last_active:
            last_active_ts = last_active.timestamp()
            if last_active_ts > last_24h:
                active_users_24h += 1
            if last_active_ts > last_7d:
                active_users_7d += 1

        # Get meals and water data
        meals_ref = users_ref.document(user.id).collection('meals')
        water_ref = users_ref.document(user.id).collection('water')
        
        user_meals = list(meals_ref.stream())
        user_water = list(water_ref.stream())
        
        total_meals += len(user_meals)
        user_water_amount = sum(w.to_dict().get('amount', 0) for w in user_water)
        total_water += user_water_amount

        # Compile user summary
        user_data_list.append({ # Renamed to avoid conflict
            'User ID': user.id,
            'Name': data.get('name', 'Unknown'),
            'Language': data.get('language', 'unknown'),
            'Goal': data.get('goal', 'unknown'),
            'Meals Logged': len(user_meals),
            'Water (L)': round(user_water_amount/1000, 2),
            'Last Active': data.get('last_active', 'Never').astimezone(UZB_TZ).strftime('%Y-%m-%d %H:%M:%S %Z') if data.get('last_active') else 'Never'
        })

    # Print Summary
    print("\n=== BiteWise Bot Usage Statistics ===\n")
    
    print(f"Total Users: {total_users}")
    print(f"Active Users (24h): {active_users_24h}")
    print(f"Active Users (7d): {active_users_7d}")
    print(f"Total Meals Logged: {total_meals}")
    print(f"Total Water Logged: {round(total_water/1000, 2)}L")
    
    print("\n=== Language Distribution ===")
    for lang, count in languages.most_common():
        print(f"{lang}: {count} users ({round(count/total_users*100, 1)}%)")
    
    print("\n=== Goals Distribution ===")
    for goal, count in goals.most_common():
        print(f"{goal}: {count} users ({round(count/total_users*100, 1)}%)")
    
    print("\n=== Gender Distribution ===")
    for gender, count in gender_count.most_common():
        print(f"{gender}: {count} users ({round(count/total_users*100, 1)}%)")
    
    print("\n=== Age Distribution ===")
    for age_range, count in age_ranges.most_common():
        print(f"{age_range}: {count} users ({round(count/total_users*100, 1)}%)")
    
    print("\n=== Activity Levels ===")
    for level, count in activity_levels.most_common():
        print(f"{level}: {count} users ({round(count/total_users*100, 1)}%)")
    
    print("\n=== Top 10 Most Active Users (by Meals Logged) ===")
    # Sort users by meals logged
    sorted_by_meals = sorted(user_data_list, key=lambda x: x['Meals Logged'], reverse=True)[:10] # Use renamed list
    print(tabulate(sorted_by_meals, headers='keys', tablefmt='grid'))

    # --- Export user summary as CSV ---
    csv_filename = 'user_stats_summary.csv'
    if user_data_list:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=user_data_list[0].keys())
            writer.writeheader()
            writer.writerows(user_data_list)
        print(f"\nUser summary exported to {csv_filename}")

    # --- New Sections ---
    print("\n=== Last 10 Registered Users ===")
    # Sort by registration_date - assuming 'registration_timestamp' field exists as a Unix timestamp
    # If 'registration_date' is a datetime object, adjust sorting key accordingly.
    # For this example, I'll assume 'registration_timestamp' or use 'created_at' if available
    # As a fallback, if no registration date field, this section might be less accurate or omitted.
    
    # Check for a registration date field. Common names might be 'registration_date', 'created_at', 'join_date'
    # We will try to find a field that is a datetime object or a timestamp.
    # For this example, let's assume there's a field 'registration_timestamp' (unix) or 'registration_date' (datetime)
    
    # Prioritize a dedicated registration timestamp field
    if all_users_for_sorting and 'registration_timestamp' in all_users_for_sorting[0]:
        sorted_by_registration = sorted(all_users_for_sorting, key=lambda x: x.get('registration_timestamp', 0), reverse=True)
    elif all_users_for_sorting and 'registration_date' in all_users_for_sorting[0] and isinstance(all_users_for_sorting[0]['registration_date'], datetime):
        sorted_by_registration = sorted(all_users_for_sorting, key=lambda x: x.get('registration_date', datetime.min.replace(tzinfo=pytz.utc)), reverse=True)
    else: # Fallback if no specific registration field - this might not be accurate for "newest"
        print("Warning: No clear registration date field found. Displaying users, but order might not reflect actual registration time.")
        sorted_by_registration = all_users_for_sorting # Or sort by another available date if one exists

    last_10_registered_display = []
    for u_data in sorted_by_registration[:10]:
        reg_date_str = "N/A"
        if 'registration_timestamp' in u_data:
            reg_date_str = datetime.fromtimestamp(u_data['registration_timestamp'], tz=pytz.utc).astimezone(UZB_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')
        elif 'registration_date' in u_data and isinstance(u_data['registration_date'], datetime):
            # Ensure the datetime object is timezone-aware (assuming UTC if naive)
            dt_obj = u_data['registration_date']
            if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
                dt_obj = pytz.utc.localize(dt_obj)
            reg_date_str = dt_obj.astimezone(UZB_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')
        
        last_10_registered_display.append({
            'User ID': u_data.get('user_id', 'Unknown'), # Assuming user_id is the key in Firestore document
            'Name': u_data.get('name', 'Unknown'),
            'Registration Date': reg_date_str
        })
    print(tabulate(last_10_registered_display, headers='keys', tablefmt='grid'))

    print("\n=== Last 10 Recently Active Users ===")
    # Sort by last_active timestamp
    # Ensure 'last_active' is a datetime object or a comparable type (e.g., timestamp)
    active_users_sorted = sorted(
        [u for u in all_users_for_sorting if u.get('last_active')],  # Filter out users with no last_active
        key=lambda x: x.get('last_active', datetime.min.replace(tzinfo=pytz.utc)), # Handle missing last_active with a default
        reverse=True
    )
    
    last_10_active_display = []
    for u_data in active_users_sorted[:10]:
        last_active_dt = u_data.get('last_active')
        last_active_str = "Never"
        if isinstance(last_active_dt, datetime):
            # Ensure the datetime object is timezone-aware (assuming UTC if naive)
            if last_active_dt.tzinfo is None or last_active_dt.tzinfo.utcoffset(last_active_dt) is None:
                last_active_dt = pytz.utc.localize(last_active_dt)
            last_active_str = last_active_dt.astimezone(UZB_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')
        elif isinstance(last_active_dt, (int, float)): # if it's a timestamp
             last_active_str = datetime.fromtimestamp(last_active_dt, tz=pytz.utc).astimezone(UZB_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')

        last_10_active_display.append({
            'User ID': u_data.get('user_id', 'Unknown'),
            'Name': u_data.get('name', 'Unknown'),
            'Last Active': last_active_str
        })
    print(tabulate(last_10_active_display, headers='keys', tablefmt='grid'))

def main():
    print("Fetching user statistics...")
    get_user_stats()

if __name__ == "__main__":
    main() 