---
name: halt-repeated-action-loops
description: Use when an action returns 'Nothing happens' or fails unexpectedly to prevent infinite retry cycles.
category: general
---

## HALT REPEATED ACTION LOOPS

**Process:**
1. Execute the intended action.
2. Analyze the observation response immediately.
3. If the response is 'Nothing happens', increment a failure counter for this specific action-target pair.
4. If the counter reaches 2, STOP attempting this action.
5. Pivot to a different strategy (e.g., search a different location or object).

**Anti-patterns:**
- Repeating the same 'take' or 'open' command more than twice despite negative feedback.
- Ignoring 'Nothing happens' messages and assuming the next attempt will succeed.

**Failure Recovery:**
- If an action fails twice, assume the object is not present or the container is inaccessible.
- Re-scan the immediate area for alternative objects or check if the container state has changed (e.g., already open).
