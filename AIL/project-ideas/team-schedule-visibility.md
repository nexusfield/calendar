---
type: project-idea
tags: [project-idea]
status: idea
priority: low
created: 2026-04-19
updated: 2026-04-19
owner: Landon
summary: "Unassigned idea — give the team direct visibility into my schedule without having to route requests through Sophie"
---

# Team Schedule Visibility

## The Problem

Right now, anyone on the team who wants to know when I'm available has to go through Sophie. That's a bottleneck — Sophie is busy, sometimes out of it, and scheduling requests drift or get dropped. Doesn't scale for me or for her.

The underlying issue isn't Sophie specifically — it's that my availability is a piece of team-critical information that has exactly one choke point.

## Why This Could Be Useful

- Zeki / Devon / Ken could book time directly instead of asking Sophie to ask me
- Reduces one category of back-and-forth that adds up across the week
- Removes a single point of failure when Sophie is stretched
- Minor: makes me look more professional / easier to work with

## Possible Approaches

| Option | What It Looks Like | Tradeoffs |
|--------|-------------------|-----------|
| **Shared Google Calendar** | Expose my work calendar read-only to the team | Simplest. Privacy concerns if personal events leak. Mitigate with a dedicated "work-availability" calendar. |
| **Cal.com / Calendly / Google Booking** | Team members book open slots directly via a link | Frictionless for them. One more tool to maintain. Tool choice matters — Cal.com is free/open-source. |
| **Status in Slack** | `/office-hours` style — post weekly availability in a channel | Low effort. Requires remembering to update. |
| **Just tell them my hours** | Send one note saying "I'm around 9-5 CT, book via X channel" | Simplest non-tool option. Works for a small team. |

## Key Questions

- Would Ken / Zeki even want this, or do they prefer routing through Sophie?
- Is there an AIL-wide calendar/scheduling convention I should just adopt?
- Does Sophie *want* to be offloaded from this, or is scheduling part of how she stays connected to people's work?

## To Move to `projects/`

- Bring up in 1:1 with Zeki
- Get green light
- Pick an option, implement in < 1 hour
