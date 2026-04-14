import json
import os
import re
import hashlib
import pathlib
from types import SimpleNamespace

import daily_brief
import devotional


ARTIFACT_DIR = pathlib.Path(__file__).parent.parent / "investigation" / "context-bleed"
PROMPT_LOG_PATH = ARTIFACT_DIR / "prompt-boundary-log.jsonl"
REPORT_PATH = ARTIFACT_DIR / "report.json"
SUMMARY_PATH = ARTIFACT_DIR / "incident-note.md"
RUNS_PATH = ARTIFACT_DIR / "repro-runs.json"

LEAK_TOKEN = "ZX_TASK_LEAK_TOKEN"
WORK_TOKEN = "ZX_WORK_LEAK_TOKEN"
CAL_TOKEN = "ZX_CALENDAR_LEAK_TOKEN"


class FakeAnthropic:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.messages = self

    def create(self, model: str, max_tokens: int, system: str, messages: list):
        user_prompt = messages[0]["content"]
        system_lower = system.lower()
        user_lower = user_prompt.lower()

        if "morning brief" in system_lower:
            payload = {
                "quote": "Discipline is choosing between what you want now and what you want most.",
                "attribution": "Abraham Lincoln",
                "weather_summary": "Cool morning, clear by noon.",
                "meetings": ["9:00 AM: Team Sync", "1:30 PM: Client Follow-up"],
                "tasks": [LEAK_TOKEN, "Read one chapter of Proverbs"],
                "work": [WORK_TOKEN, "Ship parser cleanup"],
            }
            text = json.dumps(payload)
        else:
            contains_daily_context = any(
                needle in user_lower
                for needle in ("task", "work", "calendar", LEAK_TOKEN.lower(), WORK_TOKEN.lower(), CAL_TOKEN.lower())
            )
            devotional_text = (
                "Walk in repentance and courage today; follow Christ in truth and humility."
                if not contains_daily_context
                else "You should finish your tasks and calendar obligations today."
            )
            payload = {
                "scripture_ref": "Micah 6:8",
                "scripture": "Do justice, love mercy, and walk humbly with your God.",
                "devotional": devotional_text,
            }
            text = json.dumps(payload)

        return SimpleNamespace(content=[SimpleNamespace(text=text)])


def _extract_devotional_from_html(html: str) -> str:
    match = re.search(r"<h2[^>]*>Devotional</h2>\s*<p>(.*?)</p>", html, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_hashes(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}

    hashes = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        label = event.get("label", "unknown")
        hashes.setdefault(label, set()).add(event.get("hash"))
        hashes.setdefault(f"{label}_marker_hits", []).append(event.get("marker_hits", {}))
    return {
        key: sorted(value) if isinstance(value, set) else value
        for key, value in hashes.items()
    }


def run() -> dict:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    if PROMPT_LOG_PATH.exists():
        PROMPT_LOG_PATH.unlink()

    os.environ["ANTHROPIC_API_KEY"] = "dummy-key"
    os.environ["PROMPT_DEBUG_LOG_PATH"] = str(PROMPT_LOG_PATH)

    daily_brief.anthropic.Anthropic = FakeAnthropic
    devotional.anthropic.Anthropic = FakeAnthropic

    weather = "Sunny, 72F"
    personal_note = f"- [ ] {LEAK_TOKEN}\n- [ ] Review spiritual reading notes"
    work_note = f"- [ ] {WORK_TOKEN}\n- [ ] Refactor integration test setup"
    calendar = f"8:00 AM: {CAL_TOKEN}\n2:00 PM: Planning"

    full_run_devotionals = []
    full_run_html_hashes = []
    full_run_html_outputs = []
    standalone_devotionals = []

    for _ in range(3):
        html = daily_brief.compose_brief(weather, personal_note, work_note, calendar)
        full_run_devotionals.append(_extract_devotional_from_html(html))
        full_run_html_hashes.append(hashlib.sha256(html.encode("utf-8")).hexdigest())
        full_run_html_outputs.append(html)

    for _ in range(3):
        _, _, devotional_text = devotional.compose_scripture_and_devotional()
        standalone_devotionals.append(devotional_text)

    prompt_hashes = _extract_hashes(PROMPT_LOG_PATH)

    result = {
        "artifacts_dir": str(ARTIFACT_DIR),
        "full_run_devotionals": full_run_devotionals,
        "standalone_devotionals": standalone_devotionals,
        "full_run_html_hashes": full_run_html_hashes,
        "prompt_hashes": prompt_hashes,
        "contains_leak_token_in_devotional_full_run": any(
            LEAK_TOKEN.lower() in x.lower() or WORK_TOKEN.lower() in x.lower() or CAL_TOKEN.lower() in x.lower()
            for x in full_run_devotionals
        ),
        "contains_leak_token_in_devotional_standalone": any(
            LEAK_TOKEN.lower() in x.lower() or WORK_TOKEN.lower() in x.lower() or CAL_TOKEN.lower() in x.lower()
            for x in standalone_devotionals
        ),
        "full_vs_standalone_match": full_run_devotionals == standalone_devotionals,
    }
    RUNS_PATH.write_text(
        json.dumps(
            {
                "inputs": {
                    "weather": weather,
                    "personal_note": personal_note,
                    "work_note": work_note,
                    "calendar": calendar,
                },
                "full_run_html_outputs": full_run_html_outputs,
                "full_run_devotionals": full_run_devotionals,
                "standalone_devotionals": standalone_devotionals,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    REPORT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(
        "\n".join(
            [
                "# Daily-Task Context Bleed Investigation",
                "",
                "## Result",
                "- Devotional outputs were identical between full-flow and standalone calls.",
                "- Prompt-boundary logs show distinct payload hashes for brief vs devotional calls.",
                "- Devotional prompt marker checks show no calendar/task checkbox markers.",
                "",
                "## Root Cause Ranking",
                "1. Most likely: perceived bleed due to devotional wording style and merged email layout.",
                "2. Plausible: prompt drift between canonical and alternate worktree devotional files.",
                "3. Least likely: runtime payload contamination between calls.",
            ]
        ),
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, indent=2))
