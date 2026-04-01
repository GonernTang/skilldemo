---
name: illuminate-before-look
description: Use this skill when examining an object that may be obscured by darkness or requires specific lighting conditions to be visible.
category: alfworld/look_at_obj_in_light
---

## Illuminate Before Look

**Process:**
1. Navigate to the location containing the target object.
2. Pick up the target object if it is resting on a surface.
3. Identify and activate a nearby light source (e.g., lamp, switch).
4. Ensure the environment is sufficiently illuminated before issuing the look command.

**Anti-patterns:**
- Attempting to look at an object while the room is dark.
- Ignoring local light sources like desk lamps in favor of distant overhead lights.

**Failure Recovery:**
- If the object is still not visible, search for additional light switches or move to a different light source.
- Check if the object is inside a closed container that needs to be opened first.
