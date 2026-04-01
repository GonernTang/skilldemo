---
name: container-state-verification
description: Use before interacting with any storage unit to ensure the container is in the correct state for interaction.
category: general
---

## Container State Verification

**Process:**
1. Navigate to the target container (fridge, cabinet, drawer).
2. Observe the state description ('closed' or 'open').
3. If 'closed', execute 'open' command before attempting to interact.
4. If 'open', proceed directly to interaction (take/place).

**Anti-patterns:**
- Attempting to 'take' from a container marked 'closed'.
- Assuming a container is open without reading the observation text.

**Failure Recovery:**
- If 'open' returns 'Nothing happened', verify if the container is already open in previous observations.
- If access remains blocked, search adjacent surfaces or alternative containers.
