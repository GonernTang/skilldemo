---
name: halt-repeated-action-failure
description: Use when an interaction returns 'Nothing happens' to prevent wasting steps on invalid actions.
category: general
---

## HALT REPEATED ACTION FAILURE

**Process:**
1. Execute the intended action on the target object or location.
2. Read the observation feedback immediately after the action.
3. If the result is 'Nothing happens', count the occurrence.
4. If the same action fails 2+ times, stop and select a different approach or object.

**Anti-patterns:**
- Repeating the exact same command (e.g., 'open drawer') multiple times after receiving 'Nothing happens'.
- Ignoring observation feedback and continuing the original plan regardless of errors.

**Failure Recovery:**
- Verify if the object exists in the current environment.
- Check if the container is already open or locked.
- Switch to a different target object or location entirely.
