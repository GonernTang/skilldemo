---
name: cool-item-with-fridge
description: Use when the task requires lowering an object's temperature using a refrigerator before moving it to a final location.
category: alfworld/cool
---

## Cool Item With Fridge

**Process:**
1. Pick up the target item from its current location.
2. Navigate to the nearest refrigerator.
3. Open the refrigerator door if it is currently closed.
4. Perform the cool action on the held item using the refrigerator.
5. Navigate to the specified final receptacle.
6. Move the cooled item into the final receptacle.

**Anti-patterns:**
- Do not attempt to cool an item that is not currently held in your inventory.
- Do not skip opening the refrigerator before attempting the cool action.
- Do not leave the item inside the refrigerator after cooling; ensure it is moved to the final destination.
