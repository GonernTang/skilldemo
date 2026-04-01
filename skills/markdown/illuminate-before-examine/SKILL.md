---
name: illuminate-before-examine
description: Use when the task requires verifying an object's appearance under specific lighting conditions.
category: alfworld/look_at_obj_in_light
---

## Illuminate Before Examine

**Process:**
1. Search the current room for a light source (e.g., desk lamp, floor lamp).
2. Navigate to the light source and execute "use [light_source]" to turn it on.
3. Navigate to the target object's location.
4. Execute "look at [target_object]" to confirm visibility.

**Anti-patterns:**
- Attempting to "look at" the object before ensuring the light source is active.
- Ignoring closed containers where the object might be hidden even if the room is lit.

**Failure Recovery:**
- If the light source does not turn on, search for alternative light sources in adjacent rooms.
- If the object is not visible despite lighting, systematically open nearby containers (drawers, cabinets) to locate it.
