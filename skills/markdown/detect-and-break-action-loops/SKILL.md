---
name: detect-and-break-action-loops
description: Use when an action repeatedly returns 'Nothing happened' or the agent performs redundant actions without progress.
category: general
---

## Detect and Break Action Loops

**Process:**
1. Monitor observation feedback after every action execution.
2. If 'Nothing happens' appears 2+ times consecutively, flag as a loop.
3. Immediately halt the current action sequence.
4. Re-evaluate the current state and inventory before selecting a new action.

**Anti-patterns:**
- Repeating the same command (e.g., 'stop', 'open') after receiving 'Nothing happens'.
- Continuing to execute 'None' actions when no valid options are available.

**Failure Recovery:**
- If the action fails twice, switch to a different object type or location.
- Verify if the target container is already open or the object is already held.
