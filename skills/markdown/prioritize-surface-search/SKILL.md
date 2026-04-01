---
name: prioritize-surface-search
description: Use when searching for an object to check visible surfaces before exhausting container searches.
category: general
---

## Prioritize Surface Search

**Process:**
1. Upon entering a room, scan visible surfaces (countertops, tables, shelves).
2. Attempt to take or interact with the target object on these surfaces first.
3. Only proceed to open drawers or cabinets if the object is not found on surfaces.

**Anti-patterns:**
- Opening every cabinet or drawer sequentially without checking visible areas.
- Assuming objects are always hidden inside containers rather than on top.

**Failure Recovery:**
- If container search yields no results, re-scan the room for overlooked surfaces.
- Check if the object was moved to a surface during previous interactions.
