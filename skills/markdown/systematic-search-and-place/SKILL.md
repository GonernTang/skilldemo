---
name: systematic-search-and-place
description: Use when locating a hidden object within containers and moving it to a designated target.
category: alfworld/pick_and_place
---

## Systematic Search and Place

**Process:**
1. Inspect all visible surfaces (tables, dressers) for the target object before touching containers.
2. If not found on surfaces, systematically open nearby containers (drawers, cabinets) one by one until the object is located.
3. Once located, execute 'take [object] from [container]'.
4. Navigate directly to the target placement location.
5. Execute 'move [object] to [location]' to complete the task.

**Anti-patterns:**
- Opening every container in the room randomly without prioritizing proximity or surface checks.
- Attempting to place an object without confirming you have successfully picked it up first.

**Failure Recovery:**
- If 'take' fails with 'Nothing happened', re-scan nearby surfaces or check adjacent containers for the object.
- If 'move' fails, verify the target location is valid and capable of receiving the object type.
