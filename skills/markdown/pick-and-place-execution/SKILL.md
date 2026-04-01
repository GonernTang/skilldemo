---
name: pick-and-place-execution
description: Use when moving a specific object from a source location to a target destination.
category: alfworld/pick_and_place
---

## Pick and Place Execution

**Process:**
1. Navigate to the source location where the object is expected.
2. Check visible surfaces (desks, countertops) first before assuming the object is inside a closed container.
3. Execute "take [object] from [source]" once the object is confirmed present.
4. Navigate to the destination location.
5. Execute "move [object] to [destination]".

**Anti-patterns:**
- Do not confuse "toiletpaperhanger" with "toilet" as they are distinct locations.
- Do not ignore multiple instances of an object if the task specifies a quantity (e.g., "put two X in Y").

**Failure Recovery:**
- If "take" fails, re-scan nearby surfaces as the object may be on a different visible surface than expected.
