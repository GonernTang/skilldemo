---
name: stop-repeated-action-failure
description: Use when an action returns 'Nothing happened' or fails to change state after execution.
category: general
---

## Stop Repeated Action Failure

**Process:**
1. Monitor action output for error messages like "Nothing happens" or lack of state change.
2. Count consecutive failures on the same object/location pair.
3. If count reaches 2, immediately cease the current action sequence.
4. Re-evaluate object state (is it open? is it visible?) before proceeding.

**Anti-patterns:**
- Continuing to issue the same "take" or "open" command after receiving "Nothing happens".
- Ignoring observation text that indicates the object is not accessible or present.

**Failure Recovery:**
- If "Nothing happens" persists, verify the container is actually open via observation.
- Move to a different nearby location to search for alternative instances of the object.
