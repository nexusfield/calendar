"""
daily_brief.py — Composes and sends Landon's morning email brief.
Reads:   AIL vault (daily note), Braindump vault (personal daily note)
Fetches: Baton Rouge weather (OpenWeatherMap), Google Calendar
Sends:   HTML email via Resend, content composed by Claude
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

VAULT_ROOT      = pathlib.Path(__file__).parent.parent / "ailvault" / "AIL"
BRAINDUMP_ROOT  = pathlib.Path(__file__).parent.parent / "briandump"
TIMEZONE        = datetime.timezone(datetime.timedelta(hours=-6))  # CST

BATON_ROUGE_LAT = 30.4515
BATON_ROUGE_LON = -91.1871

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


# ── 1. Weather — Baton Rouge ──────────────────────────────────────────────────

def get_weather() -> str:
    api_key = os.environ.get("OPENWEATHER_API_KEY", "")
    if not api_key:
        return "Weather not configured."

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

        return (
            f"{conditions}\n"
            f"Now: {temp:.0f}F (feels like {feels_like:.0f}F)\n"
            f"High: {day_high:.0f}F | Humidity: {humidity}% | Wind: {wind_mph:.0f} mph"
        )

    except Exception as e:
        return f"Weather unavailable ({e})."


# ── 2. AIL vault ──────────────────────────────────────────────────────────────

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
    return f"No personal note found for {today}."


# ── 3. Google Calendar ────────────────────────────────────────────────────────

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
        lines.append(f"{time_str}: {title}")

    return "\n".join(lines)


# ── 4. Compose with Claude ────────────────────────────────────────────────────

def compose_brief(
    weather:              str,
    braindump_daily_note: str,
    ail_daily_note:       str,
    calendar_events:      str,
) -> str:
    today      = datetime.datetime.now(TIMEZONE).strftime("%A, %B %-d")
    client     = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    verse_list = "\n".join(f"- {v}" for v in VERSES)

    prompt = f"""You are composing Landon's morning email brief. He is a young man, ambitious, faith-oriented, building toward something. Keep everything grounded and direct.

Today is {today}.

Here are the available scripture passages to choose from:
<verse_options>
{verse_list}
</verse_options>

Here is his calendar for today:
<calendar>
{calendar_events}
</calendar>

Here is his personal daily note (projects, research, personal tasks):
<personal_note>
{braindump_daily_note}
</personal_note>

Here is his work daily note (AIL vault):
<work_note>
{ail_daily_note}
</work_note>

Here is the weather for Baton Rouge today:
<weather>
{weather}
</weather>

Instructions:
- quote: A real quote from a real person. Historical, philosophical, literary. Thought-provoking and timeless. Not motivational fluff.
- attribution: The person's name only.
- weather_summary: One casual practical sentence about the day. Example: "May want a raincoat." or "Good day to be outside."
- meetings: List of calendar events as short strings. Empty list if none.
- tasks: Unchecked items (lines with "- [ ]") from personal note. Strip Obsidian wiki links. Empty list if none.
- work: Unchecked items (lines with "- [ ]") from work note. Strip Obsidian wiki links. Group into topic buckets, 4-6 items max.
- scripture_ref: The chosen passage reference only (e.g. "Romans 8:28-39").
- scripture: Full passage in modern plain English. Do not shorten.
- devotional: 3-4 sentences. Direct, grounded, rooted in Christ. For a man who wants to start strong. No fluff, no cliches.

Respond with a single valid JSON object and nothing else. No markdown, no code fences, just the raw JSON.

{{
  "quote": "...",
  "attribution": "...",
  "weather_summary": "...",
  "meetings": ["..."],
  "tasks": ["..."],
  "work": ["..."],
  "scripture_ref": "...",
  "scripture": "...",
  "devotional": "..."
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system="You are a personal assistant composing a private morning brief for Landon, a young Christian man. Output only valid JSON as instructed.",
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(raw)
    return render_html(data, today, weather)


def render_html(data: dict, today: str, weather: str) -> str:
    h2 = (
        'style="border-bottom: 2px solid #8aab6e; padding-bottom: 4px; '
        'font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; '
        'color: #2d4a35; margin-top: 32px;"'
    )

    def list_html(items):
        if not items:
            return "<p>None.</p>"
        lis = "".join(f"<li>{item.replace(chr(8212), '-')}</li>" for item in items)
        return f'<ul style="padding-left: 20px;">{lis}</ul>'

    meetings_html = list_html(data.get("meetings", []))
    tasks_html    = list_html(data.get("tasks", []))
    work_html     = list_html(data.get("work", []))

    def clean(text):
        return str(text).replace("\u2014", "-")

    weather_html = weather.replace("\n", "<br>")

    return f"""<div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; background-color: #fdf8f2; color: #2a2a2a; line-height: 1.7; padding: 32px;">

  <p style="font-size: 22px; font-weight: bold; margin-bottom: 4px; color: #2d4a35;">Good morning, Landon.</p>
  <p style="color: #7a7a6a; margin-top: 0;">{today}</p>

  <p style="font-style: italic; color: #3a3a2a; border-left: 3px solid #8aab6e; padding-left: 14px;">"{clean(data.get("quote", ""))}"</p>
  <p style="color: #7a7a6a; margin-top: -10px; padding-left: 17px;">- {clean(data.get("attribution", ""))}</p>

  <h2 {h2}>Weather - Baton Rouge</h2>
  <p style="white-space: pre-line;">{weather_html}</p>
  <p style="color: #6a7a5a; font-style: italic;">{clean(data.get("weather_summary", ""))}</p>

  <h2 {h2}>Meetings</h2>
  {meetings_html}

  <h2 {h2}>Tasks</h2>
  {tasks_html}

  <h2 {h2}>Work</h2>
  {work_html}

  <h2 {h2}>Scripture - {clean(data.get("scripture_ref", ""))}</h2>
  <p>{clean(data.get("scripture", ""))}</p>

  <h2 {h2}>Devotional</h2>
  <p>{clean(data.get("devotional", ""))}</p>

</div>"""


# ── 5. Send via Resend ────────────────────────────────────────────────────────

def send_email(body: str):
    resend.api_key = os.environ["RESEND_API_KEY"]
    recipient      = os.environ["RECIPIENT_EMAIL"]
    today          = datetime.datetime.now(TIMEZONE).strftime("%A %-d %b")

    resend.Emails.send({
        "from":    "onboarding@resend.dev",
        "to":      recipient,
        "subject": f"Morning Brief: {today}",
        "html":    body,
        "text":    "See HTML version.",
    })
    print(f"Brief sent to {recipient}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
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
        weather,
        braindump_daily_note, ail_daily_note, calendar_events,
    )

    print("--- BRIEF PREVIEW ---")
    print(brief)
    print("---------------------")

    print("Sending email...")
    send_email(brief)
    print("Done.")
