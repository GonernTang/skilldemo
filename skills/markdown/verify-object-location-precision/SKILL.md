---
name: verify-object-location-precision
description: Use when searching for objects to distinguish specific location names and prioritize visible surfaces.
category: general
---

## VERIFY OBJECT LOCATION PRECISION

**Process:**
1. Scan initial room observations for objects on visible surfaces (tables, counters, holders).
2. Distinguish between similar location names (e.g., 'toiletpaperhanger' vs 'toilet', 'sinkbasin' vs 'bathtub').
3. Prioritize interacting with visible surfaces before opening closed containers (drawers, cabinets).
4. Confirm the object is inside a container before attempting to take it from there.

**Anti-patterns:**
- Assuming an object is in a generic container (like 'toilet') when it is on a specific fixture (like 'toiletpaperhanger').
- Opening every drawer or cabinet sequentially without checking visible areas first.

**Failure Recovery:**
- If 'take' fails from a container, check if the container was actually opened or if the object moved.
- If location name seems wrong, look for synonyms or related fixtures in the initial observation list.
