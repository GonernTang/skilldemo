---
name: interaction-state-recovery
description: Use when an interaction command returns a failure message like 'Nothing happens'.
category: general
---

## Interaction State Recovery

**Process:**
1. Observe the system response immediately after executing an action like 'take' or 'move'.
2. If the response indicates failure (e.g., "Nothing happens"), halt further attempts on that specific state.
3. Reset the environment context by closing and reopening the container or re-navigating to the location.
4. Retry the interaction command after the state has been refreshed.

**Anti-patterns:**
- Repeating the exact same failing command multiple times without altering the environment state.
- Ignoring negative feedback messages and proceeding to unrelated tasks without resolving the blockage.
