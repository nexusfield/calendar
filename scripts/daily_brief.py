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
import hashlib
import requests
import anthropic
import resend
from devotional import compose_scripture_and_devotional
from zoneinfo import ZoneInfo
from google.oauth2 import service_account
from googleapiclient.discovery import build


# ── Config ────────────────────────────────────────────────────────────────────

VAULT_ROOT      = pathlib.Path(__file__).parent.parent / "ailvault" / "AIL"
BRAINDUMP_ROOT  = pathlib.Path(__file__).parent.parent / "briandump"
TIMEZONE        = ZoneInfo("America/Chicago")  # CST/CDT, handles daylight saving

BATON_ROUGE_LAT = 30.4515
BATON_ROUGE_LON = -91.1871


def _day_without_leading_zero(now: datetime.datetime, fmt_prefix: str) -> str:
    return f"{now.strftime(fmt_prefix)} {now.day}"


def _log_prompt_boundary(label: str, system_prompt: str, user_prompt: str):
    log_path = os.environ.get("PROMPT_DEBUG_LOG_PATH", "").strip()
    if not log_path:
        return

    payload_hash = hashlib.sha256(
        json.dumps(
            {"system": system_prompt, "user": user_prompt},
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    redacted_preview = user_prompt[:400].replace("\n", "\\n")
    marker_hits = {
        "contains_tasks_marker": ("- [ ]" in user_prompt),
        "contains_calendar_tag": ("<calendar>" in user_prompt),
        "contains_personal_note_tag": ("<personal_note>" in user_prompt),
        "contains_work_note_tag": ("<work_note>" in user_prompt),
    }

    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "source": "daily_brief",
                    "label": label,
                    "hash": payload_hash,
                    "preview": redacted_preview,
                    "marker_hits": marker_hits,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


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
    creds_json   = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    personal_id  = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
    work_id      = os.environ.get("GOOGLE_WORK_CALENDAR_ID", "")

    calendar_ids = [personal_id]
    if work_id:
        calendar_ids.append(work_id)

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

    all_events = []
    for cal_id in calendar_ids:
        try:
            result = service.events().list(
                calendarId=cal_id,
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            all_events.extend(result.get("items", []))
        except Exception as e:
            print(f"Failed to fetch calendar {cal_id}: {e}")

    if not all_events:
        return "No events today."

    # Sort merged events by start time
    def sort_key(event):
        start = event["start"].get("dateTime", event["start"].get("date", ""))
        return start

    all_events.sort(key=sort_key)

    lines = []
    for event in all_events:
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
    now = datetime.datetime.now(TIMEZONE)
    today = _day_without_leading_zero(now, "%A, %B")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    system_prompt = "You are composing a morning brief. Output only valid JSON as instructed."

    prompt = f"""You are composing Landon's morning email brief. He is a young man, ambitious and faith-oriented. Keep everything grounded and direct.

Today is {today}.

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

Respond with a single valid JSON object and nothing else. No markdown, no code fences, just the raw JSON.

{{
  "quote": "...",
  "attribution": "...",
  "weather_summary": "...",
  "meetings": ["..."],
  "tasks": ["..."],
  "work": ["..."]
}}"""
    _log_prompt_boundary(
        label="compose_brief",
        system_prompt=system_prompt,
        user_prompt=prompt,
    )

    for attempt in range(3):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Attempt {attempt + 1} failed ({e}), retrying...")

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(raw)
    scripture_ref, scripture, devotional = compose_scripture_and_devotional()
    return render_html(data, today, weather, scripture_ref, scripture, devotional)



def render_html(data: dict, today: str, weather: str, scripture_ref: str, scripture: str, devotional: str) -> str:
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

  <h2 {h2}>Scripture - {clean(scripture_ref)}</h2>
  <p>{clean(scripture)}</p>

  <h2 {h2}>Devotional</h2>
  <p>{clean(devotional)}</p>

</div>"""


# ── 5. Send via Resend ────────────────────────────────────────────────────────

def send_email(body: str):
    resend.api_key = os.environ["RESEND_API_KEY"]
    recipient      = os.environ["RECIPIENT_EMAIL"]
    now            = datetime.datetime.now(TIMEZONE)
    today          = _day_without_leading_zero(now, "%A") + f" {now.strftime('%b')}"

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
