import os
import pickle
from datetime import datetime, timezone, timedelta

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    creds = None
    token_path = 'token.pickle'
    creds_path = 'credentials.json'

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def check_availability(start_time: datetime, end_time: datetime, calendar_id='primary') -> bool:
    service = get_calendar_service()

    start_time = to_utc(start_time)
    end_time = to_utc(end_time)

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    return len(events) == 0


def book_event(summary: str, start_time: datetime, end_time: datetime, calendar_id='primary') -> str:
    service = get_calendar_service()

    start_time = to_utc(start_time)
    end_time = to_utc(end_time)

    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC'
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC'
        },
    }

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    return created_event.get('htmlLink')
def compute_free_slots(day_start: datetime, day_end: datetime, slot_duration_minutes=60, calendar_id='primary'):
    """
    Returns a list of available free time slots between day_start and day_end.
    Ensures all slots are valid, start < end, and at least slot_duration_minutes.
    """
    service = get_calendar_service()
    day_start = to_utc(day_start)
    day_end = to_utc(day_end)

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    busy_intervals = []
    for event in events:
        start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))

        start = max(start, day_start)
        end = min(end, day_end)

        if start < end:
            busy_intervals.append((start, end))

    busy_intervals.sort()

    free_slots = []
    current_start = day_start

    for busy_start, busy_end in busy_intervals:
        if current_start >= day_end:
            break

        busy_start = max(busy_start, day_start)
        busy_end = min(busy_end, day_end)

        if busy_end <= current_start:
            continue

        if (busy_start - current_start).total_seconds() / 60 >= slot_duration_minutes:
            free_slots.append((current_start, busy_start))

        current_start = busy_end


    if current_start < day_end:
        if (day_end - current_start).total_seconds() / 60 >= slot_duration_minutes:
            free_slots.append((current_start, day_end))

 
    valid_slots = []
    for s, e in free_slots:
        duration = (e - s).total_seconds() / 60
        if s < e and duration >= slot_duration_minutes and s >= day_start and e <= day_end:
            valid_slots.append((s, e))

    return valid_slots
