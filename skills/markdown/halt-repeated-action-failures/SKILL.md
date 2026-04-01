---
name: halt-repeated-action-failures
description: Use when an action returns 'Nothing happens' to avoid infinite loops and wasted steps.
category: general
---

## HALT REPEATED ACTION FAILURES

**Process:**
1. Observe the result of every action execution immediately.
2. If the observation states "Nothing happens...", count consecutive failures for the same action.
3. If the same action fails twice consecutively, immediately stop attempting it.
4. Switch to a different action type (e.g., 'go to', 'look', 'open') or target location.

**Anti-patterns:**
- Repeating the exact same command (e.g., 'take X from Y') after receiving "Nothing happens".
- Ignoring negative feedback and continuing the same interaction sequence blindly.

**Failure Recovery:**
- Perform a navigation action ('go to') to reset the agent's context.
- Re-examine the scene observation to confirm the object's actual presence and accessibility.
