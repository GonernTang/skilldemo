---
name: inspect-surfaces-first
description: Use when searching for an object to maximize efficiency and avoid blind container searching.
category: general
---

## Inspect Surfaces First

**Process:**
1. Upon arriving at a room/area, scan initial observation for "On the [location]" entries.
2. Prioritize interacting with objects listed on surfaces (countertops, desks, toilets) before opening containers.
3. Only open cabinets/drawers if the object is not found on any visible surface.

**Anti-patterns:**
- Sequentially opening every cabinet/drawer without checking room overview first.
- Assuming all objects must be stored inside closed containers.

**Failure Recovery:**
- If container search yields no results, return to the start of the room and re-read the initial observation for surface items.
- Check if the object name matches exactly (e.g., "saltshaker" vs "peppershaker") before assuming it's missing.
