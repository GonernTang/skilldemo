---
name: diagnose-and-recover-from-failure
description: Use when an action returns a negative response (e.g., 'Nothing happens') to diagnose the cause rather than repeating the same command.
category: general
---

## Diagnose and Recover from Failure

**Process:**
1. Monitor action responses for negative feedback (e.g., "Nothing happens").
2. If an action fails, stop repeating it immediately.
3. Re-evaluate the current inventory and environmental state.
4. Adjust the strategy (e.g., change object, reposition, or check compatibility) before retrying.

**Anti-patterns:**
- Repeating the same failed action consecutively without state changes.
- Ignoring failure messages and continuing with subsequent steps in the original plan.
