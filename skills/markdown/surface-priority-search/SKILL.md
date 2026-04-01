---
name: surface-priority-search
description: Use when searching for a target object to ensure surfaces are checked before opening containers.
category: alfworld/pick_and_place
---

## Surface Priority Search

**Process:**
1. Scan all visible flat surfaces (desks, tables, dressers, chairs) for the target object.
2. If the object is visible on a surface, navigate to it and pick it up.
3. Only if the object is not found on any surface, proceed to open nearby containers (drawers, cabinets).

**Anti-patterns:**
- Opening closed drawers sequentially without checking surfaces first.
- Assuming the object is inside a container just because it wasn't seen immediately.

**Failure Recovery:**
- If the 'take' action fails with 'Nothing happened', re-scan nearby surfaces for the object.
- If the object is still missing, check adjacent rooms or different container types.
