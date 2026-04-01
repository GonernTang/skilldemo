---
name: illuminate-target-before-examining
description: Use when the target object requires illumination to be seen or examined successfully.
category: alfworld/look_at_obj_in_light
---

## Ensure Object Illumination

**Process:**
1. Assess if the target object is currently visible or requires light.
2. Locate a functional light source within the same room.
3. Navigate to the light source.
4. Activate the light source (e.g., "use [light_source]").
5. Navigate to the target object.
6. Perform "look at [target_object]" to complete the task.

**Anti-patterns:**
- Ignoring lighting conditions and attempting to look at objects in dark areas.
- Attempting to physically move a fixed light source instead of activating it in place.

**Failure Recovery:**
- If the look action returns nothing, verify the light source is actually emitting light.
- If the object is still not visible, search for alternative light sources or check if the object is inside a closed container.
