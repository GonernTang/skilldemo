---
name: locate-and-illuminate-target
description: Use when you must find a specific object and ensure it is illuminated before looking at it.
category: alfworld/look_at_obj_in_light
---

## Locate and Illuminate Target

**Process:**
1. Search systematically through containers and surfaces to find the target object.
2. Pick up the target object to hold it securely.
3. Locate a nearby light source such as a lamp or switch.
4. Activate the light source to illuminate the area.
5. Execute "look at [object]" while the light is active.

**Anti-patterns:**
- Attempting to look at the object in darkness without activating a light source.
- Limiting search to only one type of furniture (e.g., only drawers) instead of checking surfaces.

**Failure Recovery:**
- If the object remains invisible, verify the light source is actually turned on and facing the object.
- If the object cannot be found, expand search to other furniture types like safes or beds.
