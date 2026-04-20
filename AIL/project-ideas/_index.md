---
type: index
tags: [project-ideas]
status: active
created: 2026-04-19
updated: 2026-04-19
summary: "Unassigned project ideas — things I think we need at AIL that could be useful, but haven't been given to me"
---

# Project Ideas

> This folder holds projects I haven't been assigned but think we should consider. Internal infrastructure, tooling, workflow fixes, product ideas — anything that surfaces from working inside AIL and seems worth building.
>
> Difference from `projects/`: those are assigned or in-progress. These are proposed.

## Why This Folder Exists

Surfacing problems is part of the job, but not every problem I notice gets handed back to me as a task. This folder is where those observations live — as concrete project pitches I can bring up in 1:1s, include in a weekly update, or pick up myself if I have capacity.

## When to Move a File to `projects/`

When someone greenlights it, assigns it, or I decide to start building it, move the file into `projects/` and flip its `status` to `active`.

## Ideas in This Folder

```dataview
TABLE summary, status, file.mtime AS "Updated"
FROM "project-ideas"
WHERE file.name != "_index"
SORT file.mtime DESC
```
