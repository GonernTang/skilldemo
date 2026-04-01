---
name: systematic-location-search
description: Use when the target object's location is unknown and requires checking multiple storage containers sequentially.
category: alfworld/pick_and_place
---

## Systematic Location Search

**Process:**
1. Identify all storage container IDs (cabinets, drawers, fridges) in the current room.
2. Navigate to the first container ID in the sequence.
3. Open the container if it is closed to reveal contents.
4. Inspect the visible items for the target object.
5. If the object is not found, proceed to the next container ID.
6. Repeat until the object is located or all containers are checked.

**Anti-patterns:**
- Do not skip containers arbitrarily; maintain a consistent order to ensure no location is missed.
- Do not persist on a container that returns 'Nothing happens'; move immediately to the next valid ID.
