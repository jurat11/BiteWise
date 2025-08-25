import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Initialize calendar service only if credentials exist
service = None
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    
    # Check if credentials.json exists
    if os.path.exists('credentials.json'):
        creds = Credentials.from_authorized_user_file('credentials.json', ['https://www.googleapis.com/auth/calendar'])
        service = build('calendar', 'v3', credentials=creds)
        logger.info("Google Calendar API initialized successfully")
    else:
        logger.warning("credentials.json not found - Google Calendar integration disabled")
except ImportError:
    logger.warning("Google API libraries not installed - Google Calendar integration disabled")
except Exception as e:
    logger.error(f"Error initializing Google Calendar API: {e}")

def get_free_slots():
    """Get available time slots from Google Calendar"""
    if not service:
        logger.warning("Google Calendar service not initialized - returning default slot")
        now = datetime.utcnow()
        return [(now.isoformat() + 'Z', (now + timedelta(hours=1)).isoformat() + 'Z')]
    
    try:
        # Calculate time range (next 7 days)
        now = datetime.utcnow()
        end_time = now + timedelta(days=7)
        
        # Call freebusy API
        body = {
            "timeMin": now.isoformat() + 'Z',
            "timeMax": end_time.isoformat() + 'Z',
            "items": [{"id": "primary"}]
        }
        
        response = service.freebusy().query(body=body).execute()
        busy_times = response.get('calendars', {}).get('primary', {}).get('busy', [])
        
        # Find gaps between busy times
        available_slots = []
        current_time = now
        
        for busy in busy_times:
            busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
            
            # If there's a gap before this busy period, add it as available
            if current_time < busy_start:
                available_slots.append((
                    current_time.isoformat() + 'Z',
                    busy_start.isoformat() + 'Z'
                ))
            
            # Move current_time pointer to the end of this busy period
            current_time = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
        
        # Add the final gap after all busy periods
        if current_time < end_time:
            available_slots.append((
                current_time.isoformat() + 'Z',
                end_time.isoformat() + 'Z'
            ))
        
        return available_slots if available_slots else [
            (now.isoformat() + 'Z', (now + timedelta(hours=1)).isoformat() + 'Z')
        ]
        
    except Exception as e:
        logger.error(f"Error getting free slots: {e}")
        # Return a default slot on error
        return [(now.isoformat() + 'Z', (now + timedelta(hours=1)).isoformat() + 'Z')]

def create_calendar_event(start, end, summary):
    """Create a calendar event and return the link"""
    if not service:
        logger.warning("Google Calendar service not initialized - skipping event creation")
        return "Calendar integration unavailable"
    
    try:
        event = {
            'summary': summary,
            'start': {'dateTime': start, 'timeZone': 'UTC'},
            'end': {'dateTime': end, 'timeZone': 'UTC'}
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return event.get('htmlLink')
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        return "Error creating calendar event"
