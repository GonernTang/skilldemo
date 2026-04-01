---
name: recover-from-action-failure
description: Use when an action returns 'Nothing happens' to diagnose the cause rather than repeating the command blindly.
category: general
---

## Recover From Action Failure

**Process:**
1. Stop immediately upon receiving a 'Nothing happens' response.
2. Navigate to the relevant location to refresh the environmental observation.
3. Re-evaluate the state of the object or container (e.g., is it still closed?).
4. Retry the action only after confirming the necessary preconditions are met.

**Anti-patterns:**
- Spamming the same action multiple times without changing position or state.
- Ignoring the failure message and proceeding to the next task step regardless of outcome.
