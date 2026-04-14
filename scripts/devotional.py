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


def compose_scripture_and_devotional() -> tuple:
    now = datetime.datetime.now()
    today = f"{now.strftime('%A, %B')} {now.day}, {now.year}"
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    system_prompt = "You select scripture and write men's devotionals."
    user_prompt = f"""Today is {today}. Pick any passage from the Bible fitting for a man starting his day. Write the most striking verse or two in modern plain English. Then write a 3-4 sentence men's devotional about the verse. Keep it strictly scripture related and drive home a specific angle of living the way of Jesus, and one way that I can practice it today.

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
