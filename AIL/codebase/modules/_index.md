---
type: index
tags: [codebase, module]
updated: 2026-04-01
---

# Modules

> All Alfie system modules. Use the module template for new entries.

```dataview
TABLE summary, status
FROM "AIL/codebase/modules"
WHERE type = "codebase" AND contains(tags, "module")
SORT file.name ASC
```
