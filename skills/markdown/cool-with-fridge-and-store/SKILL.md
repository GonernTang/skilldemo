---
name: cool-with-fridge-and-store
description: Use when you need to cool an object using a fridge and then place it into a specific receptacle.
category: alfworld/cool
---

## Cool and Store Object

**Process:**
1. Pick up the target object.
2. Navigate to a fridge and open it.
3. Execute 'cool [object] with [fridge]'.
4. Execute 'take [object] from [fridge]' to retrieve the cooled item.
5. Navigate to the correct target receptacle.
6. Place the object in the receptacle.

**Anti-patterns:**
- Do not skip the 'take from fridge' step; the object remains inside after cooling.
- Do not navigate to the wrong cabinet ID; verify the target receptacle number matches the task description.

**Failure Recovery:**
- If the object cannot be moved after cooling, return to the fridge and explicitly take the object out.
- If placed in the wrong location, close the current receptacle, retrieve the object from the fridge, and navigate to the correct one.
