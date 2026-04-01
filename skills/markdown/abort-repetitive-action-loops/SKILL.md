---
name: abort-repetitive-action-loops
description: Use immediately when an action returns 'Nothing happened' twice consecutively to prevent wasted steps and explore alternatives.
category: general
---

## REPETITIVE ACTION HALTING

**Process:**
1. Monitor the outcome of every action.
2. If an action returns "Nothing happened", record the attempt.
3. If the same action on the same target fails twice consecutively, stop immediately.
4. Switch to a different target location or action type.

**Anti-patterns:**
- Retrying the exact same `take` command on the same object ID repeatedly.
- Ignoring negative feedback messages like "Nothing happened".

**Failure Recovery:**
- Abandon the current target, scan the room for alternative valid targets, or verify if the required container needs to be opened/closed first.
