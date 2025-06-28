from fastapi import FastAPI, Query
from pydantic import BaseModel
from agent import handle_message
from calendar_service import compute_free_slots
from datetime import datetime, timedelta
import re

app = FastAPI()
@app.get("/")
def root():
    return JSONResponse(
        content={
            "message": "✅ This is the Booking Agent API! Use /chat (POST) and /availability (GET) endpoints. The frontend is here: https://booking---agent-hec2ccqjmvypajv8pgheau.streamlit.app"
        }
    )
class Message(BaseModel):
    user_message: str

def parse_requested_date(text: str) -> datetime.date:
    text = text.lower()
    today = datetime.utcnow().date()

    if text in [None, "", "tomorrow"]:
        return today + timedelta(days=1)
    if text == "today":
        return today

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

@app.post("/chat")
def chat_endpoint(msg: Message):
    reply = handle_message(msg.user_message)
    return {"response": reply}

@app.get("/availability")
def availability(date: str = Query(None, description="Date in human language (e.g. 'today', 'tomorrow', 'Monday', '2025-06-29'). Default = tomorrow.")):
    try:
        if date is None:
            target_date = datetime.utcnow().date() + timedelta(days=1)
        else:
            target_date = parse_requested_date(date)

        day_start = datetime.combine(target_date, datetime.min.time()).replace(hour=9)
        day_end = datetime.combine(target_date, datetime.min.time()).replace(hour=18)

        slots = compute_free_slots(day_start, day_end)
        if not slots:
            return {"available_slots": [], "message": f"❌ No free slots found for {target_date}."}

        pretty_slots = [
            f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')} UTC"
            for start, end in slots
        ]

        return {"available_slots": pretty_slots, "message": f"✅ Free slots found for {target_date}."}

    except Exception as e:
        return {"available_slots": [], "message": f"❌ Error: {str(e)}"}
