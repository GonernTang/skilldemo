---
name: stop-repeating-failed-actions
description: Use when an action consistently returns 'Nothing happens' or fails to change the environment state.
category: general
---

## STOP REPEATING FAILED ACTIONS

**Process:**
1. Monitor the observation feedback after every action.
2. If the same action or similar action returns 'Nothing happens' two consecutive times, immediately stop attempting it.
3. Analyze why the action failed (e.g., wrong object, closed container, incompatible appliance).
4. Select an alternative object, location, or method to achieve the sub-goal.

**Anti-patterns:**
- Continuing to execute the same command despite receiving 'Nothing happens' feedback.
- Ignoring environmental state changes (like containers closing) before retrying.

**Failure Recovery:**
- If heating fails, try a different appliance (e.g., stove instead of microwave) or check if the object is compatible.
- If taking an object fails, verify the container is open and the object is visible before retrying.
