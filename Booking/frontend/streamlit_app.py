import streamlit as st
import requests
from datetime import datetime, timedelta


API_BASE = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE}/chat"
AVAILABILITY_ENDPOINT = f"{API_BASE}/availability"

st.set_page_config(page_title="TailorTalk AI Booking Assistant", page_icon="🧵")
st.title("🧵 TailorTalk AI Booking Assistant")


if "messages" not in st.session_state:
    st.session_state.messages = []


def send_to_bot(user_message: str) -> str:
    try:
        response = requests.post(
            CHAT_ENDPOINT,
            json={"user_message": user_message},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get("response", "")).strip() or "❌ Empty response from server."
    except requests.exceptions.Timeout:
        return "❌ Connection timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "❌ Unable to connect to the server. Is it running?"
    except requests.exceptions.HTTPError as http_err:
        return f"❌ Server error: {http_err}\n\nResponse:\n{response.text}"
    except ValueError:
        return f"❌ Invalid JSON from server:\n{response.text}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"


def get_available_slots(target_date: str = None) -> str:
    try:
        params = {}
        if target_date:
            params["date"] = target_date
        response = requests.get(AVAILABILITY_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        slots = data.get("available_slots", [])
        message = data.get("message", "")

        if slots:
            slots_list = "\n".join(f"- {slot}" for slot in slots)
            return f"✅ Available slots:\n{slots_list}"
        else:
            return message
    except Exception as e:
        return f"❌ Error fetching availability: {str(e)}"


user_input = st.chat_input("Say something...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Thinking..."):
        bot_reply = send_to_bot(user_input)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

with st.expander("📅 Check availability directly"):
    st.markdown("Want to see all free slots for a date?")

    options = [
        "today",
        "tomorrow",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
        "Pick exact date"
    ]

    choice = st.selectbox("Choose date expression", options)

    if choice == "Pick exact date":
        picked_date = st.date_input("Pick a date", datetime.utcnow().date() + timedelta(days=1))
        target_date = picked_date.isoformat()
    else:
        target_date = choice

    if st.button("Check Availability"):
        with st.spinner(f"Checking available slots for {target_date}..."):
            result = get_available_slots(target_date)
            st.session_state.messages.append({"role": "assistant", "content": result})


for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.write(msg["content"])
