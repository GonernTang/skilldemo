---
name: pick-clean-place-sequence
description: Use when executing a task that requires locating, cleaning, and storing an object.
category: alfworld/clean
---

## Pick Clean Place Sequence

**Process:**
1. Locate the target object in the environment.
2. Pick up the object to ensure it is in your inventory.
3. Navigate to a sinkbasin or bathtubbasin.
4. Clean the object using the basin.
5. Navigate to the target receptacle.
6. Place the object inside the receptacle.

**Anti-patterns:**
- Attempting to clean an object without holding it in your inventory first.
- Using countertops or other surfaces instead of a sinkbasin or bathtubbasin for cleaning.

**Failure Recovery:**
- If cleaning fails, verify the object is still in inventory and the basin is accessible.
- If the target receptacle does not accept the item, check if it needs to be opened first.
