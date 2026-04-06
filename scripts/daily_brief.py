"""
daily_brief.py — Composes and sends Landon's morning email brief.
Reads: Obsidian vault (today's daily note + projects), Google Calendar
Sends: Email via Resend API, text composed by Claude
"""

import os
import json
import datetime
import pathlib
import re
import anthropic
import resend
from google.oauth2 import service_account
from googleapiclient.discovery import build


# ── Config ────────────────────────────────────────────────────────────────────

VAULT_ROOT = pathlib.Path(__file__).parent.parent / "AIL"
TIMEZONE = datetime.timezone(datetime.timedelta(hours=-6))  # CST


# ── 1. Read vault ─────────────────────────────────────────────────────────────

def read_today_daily_note() -> str:
    today = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    note_path = VAULT_ROOT / "daily" / f"{today}.md"
    if note_path.exists():
        return note_path.read_text(encoding="utf-8")
    return f"No daily note found for {today}."


def read_project_highlights() -> str:
    projects_dir = VAULT_ROOT / "projects"
    highlights = []
    for md_file in sorted(projects_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        # Pull lines that mention At Risk or upcoming deadlines
        for line in content.splitlines():
            if any(kw in line for kw in ["At Risk", "⚠", "Cota Connect", "soft launch", "blocked", "Blocked"]):
                highlights.append(f"[{md_file.stem}] {line.strip()}")
    return "\n".join(highlights) if highlights else "No flagged items in projects."


# ── 2. Read Google Calendar ───────────────────────────────────────────────────

def get_calendar_events() -> str:
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

    if not creds_json:
        return "Google Calendar not configured."

    creds_data = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_data,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )

    service = build("calendar", "v3", credentials=creds)

    now = datetime.datetime.now(TIMEZONE)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

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
        # Format time nicely if it's a datetime
        if "T" in start:
            dt = datetime.datetime.fromisoformat(start)
            time_str = dt.strftime("%-I:%M %p")
        else:
            time_str = "All day"
        title = event.get("summary", "(No title)")
        lines.append(f"  {time_str} — {title}")

    return "\n".join(lines)


# ── 3. Compose brief with Claude ─────────────────────────────────────────────

def compose_brief(daily_note: str, project_highlights: str, calendar_events: str) -> str:
    today = datetime.datetime.now(TIMEZONE).strftime("%A, %B %-d")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""You are composing a concise morning email brief for Landon, an intern at Alpha Intelligence Labs.

Today is {today}.

Here is his Obsidian daily note for today:
<daily_note>
{daily_note}
</daily_note>

Here are flagged items from his project vault:
<project_highlights>
{project_highlights}
</project_highlights>

Here are his Google Calendar events today:
<calendar_events>
{calendar_events}
</calendar_events>

Write a clean, scannable morning brief in plain text (no markdown). Format it like this:

Good morning, Landon.

TODAY — {today}

MEETINGS
  [list events, or "None" if empty]

TASKS
  [list open tasks from daily note, or "None"]

BLOCKERS
  [list blockers, or "None"]

VAULT HIGHLIGHTS
  [1-3 most important items worth knowing today, drawn from project highlights]

Keep it short. No fluff. Just what he needs to know before starting work."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


# ── 4. Send email via Resend ──────────────────────────────────────────────────

def send_email(body: str):
    resend.api_key = os.environ["RESEND_API_KEY"]
    recipient = os.environ["RECIPIENT_EMAIL"]
    today = datetime.datetime.now(TIMEZONE).strftime("%A %-d %b")

    resend.Emails.send({
        "from": "brief@resend.dev",  # update to your verified domain once set up
        "to": recipient,
        "subject": f"Morning Brief — {today}",
        "text": body,
    })
    print(f"Brief sent to {recipient}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Reading vault...")
    daily_note = read_today_daily_note()
    project_highlights = read_project_highlights()

    print("Reading Google Calendar...")
    calendar_events = get_calendar_events()

    print("Composing brief...")
    brief = compose_brief(daily_note, project_highlights, calendar_events)

    print("--- BRIEF PREVIEW ---")
    print(brief)
    print("---------------------")

    print("Sending email...")
    send_email(brief)
    print("Done.")
