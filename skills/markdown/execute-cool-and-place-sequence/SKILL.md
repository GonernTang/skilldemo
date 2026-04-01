---
name: execute-cool-and-place-sequence
description: Use this skill when the task requires picking up an object, cooling it in a fridge, and then placing it in a specific receptacle.
category: alfworld/cool
---

## Execute Cool and Place Sequence

**Process:**
1. Locate and pick up the target object.
2. Navigate to a fridge and open it if closed.
3. Execute the 'cool <object> with <fridge>' action.
4. Attempt to 'take <object> from <fridge>' if the object remains inside.
5. Navigate to the target receptacle.
6. Place the object in the receptacle.

**Anti-patterns:**
- Attempting to cool an object without first picking it up.
- Skipping the 'open fridge' step before attempting to cool.

**Failure Recovery:**
- If 'take <object> from <fridge>' returns 'Nothing happens', proceed directly to the target receptacle as the object may be ready to move.
- If the fridge is inaccessible, search other rooms for an available fridge.
