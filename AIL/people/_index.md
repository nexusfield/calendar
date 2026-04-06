---
type: index
tags: [people]
updated: 2026-04-01
---

# People

> Everyone I work with at AIL. Use the person template for new entries.

## Team

```dataview
TABLE role, status, summary
FROM "AIL/people"
WHERE type = "person"
SORT file.name ASC
```
