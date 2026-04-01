---
name: verify-prerequisite-state
description: Use when approaching an object or container to ensure it is in the correct state before attempting interaction.
category: general
---

## Verify Prerequisite State

**Process:**
1. Identify the target object or container.
2. Check the current observation for state indicators (e.g., 'open', 'closed', 'in it').
3. If the container is closed, perform 'open' action before accessing contents.
4. If the object is not visible, search nearby locations before assuming it is unreachable.

**Anti-patterns:**
- Assuming a container is open without explicitly checking the observation.
- Attempting to pick or move an object that is not listed in the current view.
