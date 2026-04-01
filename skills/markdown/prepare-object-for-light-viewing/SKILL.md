---
name: prepare-object-for-light-viewing
description: Use when the task requires viewing an object that is currently obscured by darkness or requires a specific light source to be visible.
category: alfworld/look_at_obj_in_light
---

## Prepare Object For Light Viewing

**Process:**
1. Navigate to the location where the target object is placed.
2. Pick up the target object to hold it in your inventory.
3. Navigate to a nearby light source such as a desk lamp or floor lamp.
4. Activate the light source using the 'use' action.
5. Perform 'look at [object]' to verify visibility under the light.

**Anti-patterns:**
- Do not attempt to look at the object while it remains on a surface in a dark room.
- Do not turn on the light source before securing the object if the object is hidden in shadow.

**Failure Recovery:**
- If the light does not turn on, check if you are standing close enough to the light source.
- If the object remains invisible, ensure you are holding it and facing the correct direction towards the light.
