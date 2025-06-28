from datetime import datetime, timedelta
import re
from calendar_service import check_availability, book_event, compute_free_slots

def parse_natural_language_time(user_input: str):
    if not isinstance(user_input, str):
        raise ValueError("User input must be a string.")

    text = user_input.lower()
    now = datetime.utcnow()

    days_ahead = None

    if "next week" in text:
        days_ahead = 7

    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(weekdays):
        if day in text:
            today_weekday = now.weekday()
            offset = (i - today_weekday) % 7
            if offset == 0:
                offset = 7 
            days_ahead = offset

    if "today" in text:
        days_ahead = 0
    elif "tomorrow" in text:
        days_ahead = 1

    if days_ahead is None:
        days_ahead = 1  

    target_date = now + timedelta(days=days_ahead)

    
    start_hour = 10
    end_hour = 11

    match = re.search(r'between\s+(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(am|pm)?', text)
    if match:
        start_hour = int(match.group(1))
        end_hour = int(match.group(2))
        ampm = match.group(3)
        if ampm == "pm":
            if start_hour < 12:
                start_hour += 12
            if end_hour < 12:
                end_hour += 12
    else:
        
        match_simple = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text)
        if match_simple:
            hour = int(match_simple.group(1))
            minute = int(match_simple.group(2) or 0)
            ampm = match_simple.group(3)
            if ampm == "pm" and hour < 12:
                hour += 12
            start_hour = hour
            end_hour = hour + 1
        else:
            match_hour = re.search(r'(\d{1,2})\s*(am|pm)', text)
            if match_hour:
                hour = int(match_hour.group(1))
                ampm = match_hour.group(2)
                if ampm == "pm" and hour < 12:
                    hour += 12
                start_hour = hour
                end_hour = hour + 1

  
    start_hour = max(9, min(start_hour, 17))
    end_hour = max(start_hour + 1, min(end_hour, 18))

    start = target_date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end = target_date.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    return start, end


def parse_requested_date(text: str) -> datetime.date:
    text = text.lower()
    today = datetime.utcnow().date()

    if "today" in text:
        return today
    if "tomorrow" in text:
        return today + timedelta(days=1)

    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(weekdays):
        if day in text:
            days_ahead = (i - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)

    match = re.search(r'(\d{4})[-/](\d{2})[-/](\d{2})', text)
    if match:
        y, m, d = map(int, match.groups())
        return datetime(y, m, d).date()

    return today + timedelta(days=1)

def handle_message(user_message: str):
    try:
        text = user_message.lower()

        if any(kw in text for kw in ["show availability", "available slots", "free times", "free slots"]):
            target_date = parse_requested_date(user_message)

            day_start = datetime.combine(target_date, datetime.min.time()).replace(hour=9)
            day_end = datetime.combine(target_date, datetime.min.time()).replace(hour=18)

            slots = compute_free_slots(day_start, day_end)
            if not slots:
                return f"❌ Sorry, no free slots found for {target_date}."

            pretty_slots = "\n".join(
                f"- {s.strftime('%H:%M')}–{e.strftime('%H:%M')} UTC" for s, e in slots
            )
            return f"✅ Available slots for {target_date}:\n{pretty_slots}"

     
        start_time, end_time = parse_natural_language_time(user_message)

        is_available = check_availability(start_time, end_time)

        if is_available:
            link = book_event("Meeting with AI Assistant", start_time, end_time)
            start_str = start_time.strftime("%Y-%m-%d %H:%M UTC")
            return f"✅ Your meeting is booked for {start_str}!\n[View on Calendar]({link})"
        else:
           
            target_date = start_time.date()
            day_start = datetime.combine(target_date, datetime.min.time()).replace(hour=9)
            day_end = datetime.combine(target_date, datetime.min.time()).replace(hour=18)

            slots = compute_free_slots(day_start, day_end)
            if not slots:
                return f"❌ Sorry, that time is not available, and there are no other free slots on {target_date}."

            pretty_slots = "\n".join(
                f"- {s.strftime('%H:%M')}–{e.strftime('%H:%M')} UTC" for s, e in slots
            )
            return f"❌ Sorry, that time is not available.\n✅ But here are other free slots on {target_date}:\n{pretty_slots}"

    except Exception as e:
        return f"❌ Error processing request: {str(e)}"

