import os
import datetime
from langchain_core.tools import tool
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def _get_calendar_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Find the client_secret file in the current directory
            client_secret_file = None
            for f in os.listdir('.'):
                if f.startswith('client_secret_') and f.endswith('.json'):
                    client_secret_file = f
                    break
            
            if not client_secret_file:
                raise FileNotFoundError("Could not find a client_secret_*.json file in the root directory.")
                
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            creds = flow.run_local_server(port=8080)
            
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

@tool
def create_vip_alarm(event_title: str, description: str) -> str:
    """Creates a 1-minute Google Calendar event to act as an alarm/notification for Yuvraj when a VIP messages him. Provide the title and description."""
    try:
        service = _get_calendar_service()
        
        now = datetime.datetime.utcnow()
        start_time = now + datetime.timedelta(minutes=1)
        end_time = start_time + datetime.timedelta(minutes=5)
        
        event = {
            'summary': event_title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 0},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Successfully created VIP alarm calendar event: {event.get('htmlLink')}"
    except Exception as e:
        return f"Failed to create VIP alarm on Google Calendar: {str(e)}"
