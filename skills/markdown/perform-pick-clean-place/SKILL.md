---
name: perform-pick-clean-place
description: Use when retrieving an item, cleaning it at a sink, and placing it in a target receptacle.
category: alfworld/clean
---

## Perform Pick-Clean-Place Task

**Process:**
1. Search for the target object in containers (cabinets, fridges, shelves) and navigate to its location.
2. Open the container if necessary and execute 'take <object> from <location>' to add it to inventory.
3. Navigate to a valid cleaning source ('sinkbasin' or 'bathtubbasin').
4. Execute 'clean <object> with <source>' while holding the object.
5. Navigate to the target receptacle specified in the task.
6. Execute 'move <object> to <receptacle>' to complete the task.

**Anti-patterns:**
- Do not attempt to clean an object unless it is currently in your inventory.
- Do not use non-basin surfaces (countertops, tables, shelves) as the cleaning location.

**Failure Recovery:**
- If the object cannot be found, systematically open closed containers in nearby rooms.
- If the cleaning action fails, verify the sinkbasin is open and accessible, then retry.
