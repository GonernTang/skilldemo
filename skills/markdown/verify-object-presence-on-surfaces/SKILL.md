---
name: verify-object-presence-on-surfaces
description: Use when searching for an object to confirm visibility on surfaces before searching inside containers.
category: general
---

## VERIFY OBJECT PRESENCE ON SURFACES

**Process:**
1. Identify all visible surfaces (countertops, tables, shelves) in the current view.
2. Read the observation list carefully to confirm the target object is explicitly listed.
3. Attempt interaction only if the object is confirmed in the observation.
4. Only open drawers/cabinets if the object is not found on any visible surface.

**Anti-patterns:**
- Assuming an object exists on a surface because the task requires it, even if not listed in observations.
- Opening multiple containers sequentially without checking visible surfaces first.

**Failure Recovery:**
- If an object is not found on surfaces, systematically check containers one by one rather than guessing IDs.
- If 'Nothing happens' occurs during surface interaction, verify the object name matches exactly (e.g., 'cup' vs 'mug').
