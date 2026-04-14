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
- Encouragement: Write 1-2 punchy sentences to open the day. Direct, personal, grounded in who he is. Not a pep talk. No cliches.
- Quote of the Day: Pick a real quote from a real person — historical, philosophical, literary, whatever. Thought-provoking and timeless. Not motivational fluff. Attribute it with the person's name.
- Scripture: Pick the ONE passage most fitting for a man starting his day with purpose. Write it in modern plain English, accurate to the meaning, readable. Do not shorten it.
- Devotional: 3-4 sentences. Direct, grounded, rooted in Christ. For a man who wants to start strong. No fluff, no cliches. Write it like you mean it.
- Weather summary: Based on the weather data, write one casual sentence about what kind of day it'll be. Practical, not poetic. Examples: "May want a raincoat." or "Good day to be outside." or "Hot and muggy — stay hydrated."
- Tasks: Extract only unchecked items (lines starting with "- [ ]") from the personal note. Strip Obsidian wiki links like [[...]]. Keep each item short.
- Work: Extract only unchecked items (lines starting with "- [ ]") from the work note. Strip Obsidian wiki links like [[...]]. Group related items into short topic buckets (e.g. "HubSpot CRM", "Doc Parser", "Sophie follow-ups") with a count or brief summary. Do not list every individual sub-task. Aim for 4-6 topic lines max.
- Use NO em dashes (the long dash character) anywhere in the output.
- Output valid HTML only. No markdown. No plain text outside of HTML tags.

Use this exact HTML structure and fill in each section:

<div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; background-color: #fdf8f2; color: #2a2a2a; line-height: 1.7; padding: 32px;">

  <p style="font-size: 22px; font-weight: bold; margin-bottom: 4px; color: #2d4a35;">Good morning, Landon.</p>
  <p style="color: #7a7a6a; margin-top: 0;">{today}</p>

  <p style="font-style: italic; color: #3a3a2a; border-left: 3px solid #8aab6e; padding-left: 14px;">[ENCOURAGEMENT]</p>

  <h2 style="border-bottom: 2px solid #8aab6e; padding-bottom: 4px; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; color: #2d4a35; margin-top: 32px;">Quote of the Day</h2>
  <p style="font-style: italic;">"[QUOTE]"</p>
  <p style="color: #7a7a6a; margin-top: -8px;">- [PERSON]</p>

  <h2 style="border-bottom: 2px solid #8aab6e; padding-bottom: 4px; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; color: #2d4a35; margin-top: 32px;">Weather - Baton Rouge</h2>
  <p style="white-space: pre-line;">[WEATHER BLOCK - copy exactly as given]</p>
  <p style="color: #6a7a5a; font-style: italic;">[WEATHER SUMMARY - one casual sentence]</p>

  <h2 style="border-bottom: 2px solid #8aab6e; padding-bottom: 4px; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; color: #2d4a35; margin-top: 32px;">Meetings</h2>
  [<ul style="padding-left: 20px;"><li> per event</ul> OR <p>None.</p>]

  <h2 style="border-bottom: 2px solid #8aab6e; padding-bottom: 4px; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; color: #2d4a35; margin-top: 32px;">Tasks</h2>
  [<ul style="padding-left: 20px;"><li> per unchecked item</ul> OR <p>None.</p>]

  <h2 style="border-bottom: 2px solid #8aab6e; padding-bottom: 4px; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; color: #2d4a35; margin-top: 32px;">Work</h2>
  [<ul style="padding-left: 20px;"><li> per unchecked item</ul> OR <p>None.</p>]

  <h2 style="border-bottom: 2px solid #8aab6e; padding-bottom: 4px; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; color: #2d4a35; margin-top: 32px;">Scripture - [REFERENCE]</h2>
  <p>[PASSAGE in modern plain English. Do not shorten.]</p>

  <h2 style="border-bottom: 2px solid #8aab6e; padding-bottom: 4px; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; color: #2d4a35; margin-top: 32px;">Devotional</h2>
  <p>[DEVOTIONAL]</p>

</div>"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system="You are a personal assistant composing a private morning brief for Landon, a young Christian man. The brief includes his daily tasks, weather, calendar, and a scripture passage with devotional. The personal notes you receive are private journal-style reflections and should be treated pastorally and with discretion.",
        messages=[{"role": "user", "content": prompt}],
    )

    body = message.content[0].text.strip()

    # Strip markdown code fences if Claude wrapped the HTML
    if body.startswith("```"):
        body = body.split("\n", 1)[1]
        body = body.rsplit("```", 1)[0].strip()

    # Guarantee no em dashes regardless of Claude's output
    body = body.replace("\u2014", "-")

    return body


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
