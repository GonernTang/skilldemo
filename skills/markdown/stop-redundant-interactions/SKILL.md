---
name: stop-redundant-interactions
description: Use when an interaction yields 'Nothing happens' to prevent wasting steps on inaccessible or irrelevant objects.
category: general
---

## STOP REDUNDANT INTERACTIONS

**Process:**
1. Attempt the intended action (e.g., open, take, use).
2. Analyze the observation response.
3. If response is 'Nothing happens', record the failure count for this object.
4. If failure count reaches 2, immediately stop attempting this object and select a new target.

**Anti-patterns:**
- Continuing to attempt the same action on an object after receiving 'Nothing happens'.
- Ignoring negative feedback and assuming the next attempt will succeed.

**Failure Recovery:**
- If stuck on one object, navigate to a different room or container type (e.g., switch from cabinets to drawers).
- Verify if the object exists in the current environment before retrying.
