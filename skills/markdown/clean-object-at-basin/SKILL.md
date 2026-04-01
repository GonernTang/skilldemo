---
name: clean-object-at-basin
description: Use when an object in inventory requires cleaning at a designated washing station.
category: alfworld/clean
---

## Perform Clean Operation

**Process:**
1. Ensure the target object is currently held in your inventory.
2. Navigate to a valid cleaning location (sinkbasin or bathtubbasin).
3. Execute the clean command: 'clean <object> with <location>'.
4. Verify the object status is clean before attempting to place it.

**Anti-patterns:**
- Attempting to clean an object that is not currently in your inventory.
- Using non-washing surfaces (countertops, tables) as the cleaning source.

**Failure Recovery:**
- If the clean action fails, confirm the object is dirty and the basin is not obstructed.
- If the task fails after cleaning, verify the placement destination matches the specific receptacle required and do not manually signal 'task complete' until the environment confirms success.
