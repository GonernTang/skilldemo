---
name: execute-pick-and-place
description: Use when instructed to move an item from its current location to a specified destination.
category: alfworld/pick_and_place
---

## Execute Pick And Place

**Process:**
1. Navigate to the source location where the target object is located.
2. Verify the object is present and take it into your inventory.
3. Navigate to the specified destination location.
4. Place the held object onto the destination surface.

**Anti-patterns:**
- Attempting to move an object without first picking it up.
- Navigating to the destination before successfully acquiring the object.
