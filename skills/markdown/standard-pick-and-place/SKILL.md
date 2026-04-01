---
name: standard-pick-and-place
description: Use when instructed to move a specific object from its current location to a designated target.
category: alfworld/pick_and_place
---

## Standard Pick And Place

**Process:**
1. Identify the target object and destination from the task description.
2. Check visible surfaces (tables, desks, shelves) for the object before opening any containers.
3. Navigate to the object's location and execute 'take [object]'.
4. Navigate to the target container or surface.
5. Execute 'move [object] to [target]'.

**Anti-patterns:**
- Opening drawers or cabinets before verifying the object isn't on a nearby surface.
- Attempting to place an object while holding nothing or holding the wrong item.

**Failure Recovery:**
- If 'take' returns 'Nothing happened', search adjacent surfaces or check if the object is inside an open container.
- If 'move' fails, verify the target container is open and accessible.
