---
name: illuminate-and-inspect-object
description: Use when the task requires viewing an object under illumination, ensuring the light source is activated before attempting to locate or inspect the target.
category: alfworld/look_at_obj_in_light
---

## Illuminate and Inspect Object

**Process:**
1. Identify the required light source (e.g., DeskLamp) in the current room.
2. Navigate to the light source and activate it (e.g., `use desklamp`).
3. Systematically scan the illuminated area for the target object.
4. Execute `look at <target_object>` to confirm visibility and complete the task.

**Anti-patterns:**
- Searching for the target object in the dark before activating the light source.
- Activating the light but failing to focus on the target, instead opening unrelated drawers or moving aimlessly.

**Failure Recovery:**
- If the object is not found immediately after lighting, re-examine all surfaces in the room as the light may reveal previously hidden items.
