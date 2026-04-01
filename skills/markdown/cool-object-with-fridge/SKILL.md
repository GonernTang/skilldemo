---
name: cool-object-with-fridge
description: Use when you need to lower the temperature of an object using a refrigerator before placing it elsewhere.
category: alfworld/cool
---

## Cool Object With Fridge

**Process:**
1. Navigate to the refrigerator and open it if it is currently closed.
2. Go to the location where the target object is situated.
3. Take the object into your inventory.
4. Return to the refrigerator location.
5. Execute the cool action on the object using the refrigerator.
6. Navigate to the final destination receptacle.
7. Move the cooled object to the destination.

**Anti-patterns:**
- Do not attempt to cool an object while the refrigerator door is closed.
- Do not place the object in the final destination before confirming the cooling action is complete.

**Failure Recovery:**
- If the cool action fails, verify the refrigerator is open and retry the open command before attempting to cool again.
