---
name: pick-and-place-surface
description: Use when moving a visible object from one surface to another without needing to open containers.
category: alfworld/pick_and_place
---

## Surface-to-Surface Transfer

**Process:**
1. Identify source and destination surfaces from observations.
2. Navigate to the source surface.
3. Verify the object is visible on the surface.
4. Execute 'take [object] from [source]'.
5. Navigate to the destination surface.
6. Execute 'move [object] to [destination]'.

**Anti-patterns:**
- Do not open containers if the object is clearly visible on a surface.
- Do not assume the object is still in place if the 'take' command returns "Nothing happened".

**Failure Recovery:**
- If 'take' fails, re-scan nearby surfaces for the object.
- Verify the object name matches exactly what is listed in the observation.
