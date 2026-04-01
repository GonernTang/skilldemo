---
name: sequential-storage-inspection
description: Use when the target object is not immediately visible upon arrival at a room.
category: general
---

## Sequential Storage Inspection

**Process:**
1. Upon arriving in a room, identify all potential storage containers (drawers, cabinets, shelves).
2. Iterate through each container sequentially, opening it to inspect contents.
3. If the target object is located, cease searching and proceed to interact.
4. If the object is not found, close the container and move to the next candidate.

**Anti-patterns:**
- Assuming the object is in a specific container type (e.g., only drawers) without verifying others.
- Skipping containers or failing to open them to check internal states.
