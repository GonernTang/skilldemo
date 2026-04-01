---
name: search-and-interact-with-container
description: Use when navigating through multiple storage units to locate and retrieve a specific item.
category: alfworld/pick_and_place
---

## Search and Interact with Container

**Process:**
1. Navigate to the target storage unit (e.g., drawer, cabinet).
2. Open the unit to reveal its contents.
3. Inspect the visible items for the task-specific target object.
4. If the target is found, execute the 'pick' action immediately.
5. If the target is not found, close the unit and move to the next candidate.

**Anti-patterns:**
- Opening and closing containers repeatedly without executing a 'pick' action on identified targets.
- Focusing solely on navigation and container state changes without executing manipulation actions.
