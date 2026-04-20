"""
devotional.py — Selects a Bible passage and writes a men's devotional.
Completely isolated from the rest of the daily brief pipeline.
"""

import os
import json
import datetime
import hashlib
import anthropic


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

    user_lower = user_prompt.lower()
    marker_hits = {
        "contains_tasks_word": ("task" in user_lower),
        "contains_work_word": ("work" in user_lower),
        "contains_calendar_word": ("calendar" in user_lower),
        "contains_bracket_tasks_marker": ("- [ ]" in user_prompt),
    }

    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "source": "devotional",
                    "label": label,
                    "hash": payload_hash,
                    "preview": user_prompt[:400].replace("\n", "\\n"),
                    "marker_hits": marker_hits,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


_BIBLE_BOOKS = [
    "Psalms", "Proverbs", "Matthew", "Luke", "John", "Romans",
    "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "James", "1 Peter", "Hebrews",
    "Isaiah", "Jeremiah", "Ezekiel", "Genesis", "Exodus",
    "Joshua", "Judges", "1 Samuel", "2 Samuel", "1 Kings",
    "Job", "Ecclesiastes", "Acts", "Revelation", "Mark",
    "2 Timothy", "Titus", "Nehemiah", "Daniel", "Micah",
]

_NEVER_REUSE = [
    "Mark 10:45", "John 3:16", "Philippians 4:13", "Proverbs 3:5-6",
    "Joshua 1:9", "Romans 8:28", "Jeremiah 29:11", "Matthew 6:33",
]


def compose_scripture_and_devotional() -> tuple:
    now = datetime.datetime.now()
    today = f"{now.strftime('%A, %B')} {now.day}, {now.year}"
    # Pick book deterministically from date so it rotates every day
    book = _BIBLE_BOOKS[now.timetuple().tm_yday % len(_BIBLE_BOOKS)]
    never = ", ".join(_NEVER_REUSE)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    system_prompt = "You select scripture and write men's devotionals."
    user_prompt = f"""Today is {today}. Pick a specific passage from the book of {book}. Do NOT use any of these overused verses: {never}. Choose something less commonly cited but genuinely powerful. Write the most striking verse or two in modern plain English. Then write a 3-4 sentence men's devotional about the verse. Keep it strictly scripture related and drive home a specific angle of living the way of Jesus, and one way that I can practice it today.

Respond with JSON only:
{{"scripture_ref": "...", "scripture": "...", "devotional": "..."}}"""
    _log_prompt_boundary(
        label="compose_scripture_and_devotional",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    result = json.loads(raw)
    return (
        result.get("scripture_ref", ""),
        result.get("scripture", ""),
        result.get("devotional", "").replace("\u2014", "-"),
    )
