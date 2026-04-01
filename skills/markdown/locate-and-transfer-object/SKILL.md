---
name: locate-and-transfer-object
description: Use when moving an object from a source location to a specific target destination.
category: alfworld/pick_and_place
---

## Locate And Transfer Object

**Process:**
1. Scan nearby surfaces for the object before opening any containers.
2. Navigate to the source location where the object is located.
3. Execute 'take [object] from [source]' to acquire the item.
4. Navigate to the target location (e.g., toiletpaperhanger).
5. Execute 'move [object] to [target]' to complete placement.

**Anti-patterns:**
- Do not confuse distinct locations like 'toilet' and 'toiletpaperhanger'.
- Do not attempt to take an object without confirming it is visible on the surface.

**Failure Recovery:**
- If 'take' fails, re-scan nearby surfaces or check adjacent containers.
- If 'move' fails, verify the target location is accessible and not full.
