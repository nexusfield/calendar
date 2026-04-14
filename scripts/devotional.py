"""
devotional.py — Selects a Bible passage and writes a men's devotional.
Completely isolated from the rest of the daily brief pipeline.
"""

import os
import json
import datetime
import anthropic


def compose_scripture_and_devotional() -> tuple:
    today = datetime.datetime.now().strftime("%A, %B %-d, %Y")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system="You select scripture and write men's devotionals.",
        messages=[{"role": "user", "content": f"""Today is {today}. Pick any passage from the Bible fitting for a man starting his day. Write the most striking verse or two in modern plain English. Then write a 3-4 sentence men's devotional about the verse. Keep it strictly scripture related and drive home a specific angle of living the way of Jesus, and one way that I can practice it today.

Respond with JSON only:
{{"scripture_ref": "...", "scripture": "...", "devotional": "..."}}"""}],
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
