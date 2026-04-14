"""
daily_brief.py — Composes and sends Landon's morning email brief.
Reads:   AIL vault (daily note + projects), Braindump vault (personal journal)
Fetches: Baton Rouge weather (OpenWeatherMap)
Sends:   Email via Resend, text composed by Claude
         Claude reads the journal and picks the most fitting scripture passage.
"""

import os
import json
import datetime
import pathlib
import requests
import anthropic
import resend
from google.oauth2 import service_account
from googleapiclient.discovery import build


# ── Config ────────────────────────────────────────────────────────────────────

VAULT_ROOT      = pathlib.Path(__file__).parent.parent / "AIL"
BRAINDUMP_ROOT  = pathlib.Path(__file__).parent.parent / "briandump"
TIMEZONE        = datetime.timezone(datetime.timedelta(hours=-6))  # CST

BATON_ROUGE_LAT = 30.4515
BATON_ROUGE_LON = -91.1871

# Claude picks from this list based on the journal entry.
# It knows these passages well enough to write them accurately from memory.
VERSES = [
    "Romans 5:1-5",
    "Romans 8:1-11",
    "Romans 8:28-39",
    "Romans 12:1-2",
    "Romans 6:1-11",
    "Romans 3:21-26",
    "Romans 8:14-17",
    "Romans 11:33-36",
    "John 14:1-6",
    "John 14:15-21",
    "John 15:1-11",
    "John 15:12-17",
    "John 10:7-18",
    "John 11:25-26",
    "John 16:31-33",
    "John 17:1-19",
    "Matthew 5:1-12",
    "Matthew 5:43-48",
    "Matthew 6:25-34",
    "Matthew 11:28-30",
    "Matthew 16:24-26",
    "Matthew 28:18-20",
    "Revelation 2:1-7",
    "Revelation 3:14-22",
    "Revelation 21:1-7",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def uv_label(value: float) -> str:
    if value < 3:  return "Low"
    if value < 6:  return "Moderate"
    if value < 8:  return "High"
    if value < 11: return "Very High"
    return "Extreme"


# ── 1. Journal — Braindump vault ──────────────────────────────────────────────

def read_journal() -> str:
    """
    Looks for a journal entry from last night (yesterday) or today.
    Checks yesterday first since the entry is written the evening before.
    """
    now       = datetime.datetime.now(TIMEZONE)
    yesterday = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    today     = now.strftime("%Y-%m-%d")

    for date_str in [yesterday, today]:
        path = BRAINDUMP_ROOT / "journal" / f"{date_str}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")

    return "No journal entry found."


# ── 2. Weather — Baton Rouge ──────────────────────────────────────────────────

def get_weather() -> str:
    api_key = os.environ.get("OPENWEATHER_API_KEY", "")
    if not api_key:
        return "Weather not configured — add OPENWEATHER_API_KEY to repo secrets."

    base   = "https://api.openweathermap.org/data/2.5"
    coords = f"lat={BATON_ROUGE_LAT}&lon={BATON_ROUGE_LON}&appid={api_key}&units=imperial"

    try:
        current    = requests.get(f"{base}/weather?{coords}", timeout=10).json()
        temp       = current["main"]["temp"]
        feels_like = current["main"]["feels_like"]
        humidity   = current["main"]["humidity"]
        conditions = current["weather"][0]["description"].capitalize()
        wind_mph   = current["wind"]["speed"]

        forecast = requests.get(f"{base}/forecast?{coords}&cnt=8", timeout=10).json()
        day_high = max(item["main"]["temp_max"] for item in forecast["list"])

        uv_resp  = requests.get(
            f"{base}/uvi?lat={BATON_ROUGE_LAT}&lon={BATON_ROUGE_LON}&appid={api_key}",
            timeout=10,
        ).json()
        uv_value = uv_resp.get("value", None)
        uv_str   = f"{uv_value} — {uv_label(uv_value)}" if uv_value is not None else "N/A"

        return (
            f"  {conditions}\n"
            f"  Now: {temp:.0f}°F  (feels like {feels_like:.0f}°F)\n"
            f"  High: {day_high:.0f}°F  |  Humidity: {humidity}%  |  Wind: {wind_mph:.0f} mph\n"
            f"  UV Index: {uv_str}"
        )

    except Exception as e:
        return f"Weather unavailable ({e})."


# ── 3. AIL vault ──────────────────────────────────────────────────────────────

def read_today_daily_note() -> str:
    today     = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    note_path = VAULT_ROOT / "daily" / f"{today}.md"
    if note_path.exists():
        return note_path.read_text(encoding="utf-8")
    return f"No daily note found for {today}."


def read_braindump_daily_note() -> str:
    today     = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    note_path = BRAINDUMP_ROOT / "daily" / f"{today}.md"
    if note_path.exists():
        return note_path.read_text(encoding="utf-8")
    return f"No school note found for {today}."


# ── 4. Google Calendar ────────────────────────────────────────────────────────

def get_calendar_events() -> str:
    creds_json  = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

    if not creds_json:
        return "Google Calendar not configured."

    creds_data = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_data,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    service = build("calendar", "v3", credentials=creds)

    now          = datetime.datetime.now(TIMEZONE)
    start_of_day = now.replace(hour=0,  minute=0,  second=0,  microsecond=0).isoformat()
    end_of_day   = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_of_day,
        timeMax=end_of_day,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    if not events:
        return "No events today."

    lines = []
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date", ""))
        if "T" in start:
            dt       = datetime.datetime.fromisoformat(start)
            time_str = dt.strftime("%-I:%M %p")
        else:
            time_str = "All day"
        title = event.get("summary", "(No title)")
        lines.append(f"  {time_str} — {title}")

    return "\n".join(lines)


# ── 5. Compose with Claude ────────────────────────────────────────────────────

def compose_brief(
    journal:              str,
    weather:              str,
    braindump_daily_note: str,
    ail_daily_note:       str,
    calendar_events:      str,
) -> str:
    today  = datetime.datetime.now(TIMEZONE).strftime("%A, %B %-d")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    verse_list = "\n".join(f"- {v}" for v in VERSES)

    prompt = f"""You are composing Landon's morning email brief. He is a young man — ambitious, faith-oriented, building toward something. Keep everything grounded and direct.

Today is {today}.

Here is his personal journal entry from last night:
<journal>
{journal}
</journal>

Here are the available scripture passages to choose from:
<verse_options>
{verse_list}
</verse_options>

Here is his calendar for today:
<calendar>
{calendar_events}
</calendar>

Here is his school daily note (Braindump vault):
<school_note>
{braindump_daily_note}
</school_note>

Here is his work daily note (AIL vault):
<work_note>
{ail_daily_note}
</work_note>

Here is the weather for Baton Rouge today:
<weather>
{weather}
</weather>

Instructions:
- Read the journal carefully. Pick the ONE passage from the list that speaks most directly to what he is carrying, struggling with, or needs to hear. Do not explain your choice.
- Write the full KJV passage text from memory — do not summarize or shorten it.
- Write the devotional to speak directly to what he shared in the journal.
- For SCHOOL and WORK: extract only unchecked to-do items (lines with "- [ ]"). Keep each item short. If none, write "None."

Write the brief in plain text — no markdown, no asterisks. Use this exact format:

Good morning, Landon.

{today}

WEATHER — Baton Rouge
[Copy the weather block exactly as given.]

MEETINGS
[List calendar events with times. If none, write "None."]

SCHOOL
[Unchecked to-do items from school note, short list. If none, write "None."]

WORK
[Unchecked to-do items from work note, short list. If none, write "None."]

SCRIPTURE — [chosen reference] (KJV)
[Full passage text written from memory. Do not shorten.]

DEVOTIONAL
[3-4 sentences. Speak directly to what he wrote last night. Personal, grounding, not preachy. No clichés. Write it like you mean it.]"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


# ── 6. Send via Resend ────────────────────────────────────────────────────────

def send_email(body: str):
    resend.api_key = os.environ["RESEND_API_KEY"]
    recipient      = os.environ["RECIPIENT_EMAIL"]
    today          = datetime.datetime.now(TIMEZONE).strftime("%A %-d %b")

    resend.Emails.send({
        "from":    "onboarding@resend.dev",
        "to":      recipient,
        "subject": f"Morning Brief — {today}",
        "text":    body,
    })
    print(f"Brief sent to {recipient}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Reading journal...")
    journal = read_journal()

    print("Fetching weather...")
    weather = get_weather()

    print("Reading Braindump daily note...")
    braindump_daily_note = read_braindump_daily_note()

    print("Reading AIL vault...")
    ail_daily_note = read_today_daily_note()

    print("Reading Google Calendar...")
    calendar_events = get_calendar_events()

    print("Composing brief...")
    brief = compose_brief(
        journal, weather,
        braindump_daily_note, ail_daily_note, calendar_events,
    )

    print("--- BRIEF PREVIEW ---")
    print(brief)
    print("---------------------")

    print("Sending email...")
    send_email(brief)
    print("Done.")
