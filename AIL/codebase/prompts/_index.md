---
type: index
tags: [codebase, prompt]
updated: 2026-04-01
---

# Prompts

> All prompts in the Alfie system. Use the prompt-note template for new entries.

```dataview
TABLE summary, version, status
FROM "AIL/codebase/prompts"
WHERE type = "codebase" AND contains(tags, "prompt")
SORT file.name ASC
```
