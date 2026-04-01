---
name: fail-to-adapt-strategy
description: The agent persists with failing actions or search patterns despite receiving negative feedback, rather than reassessing the situation.
category: common_mistakes
---

## Do Not Persist With Failing Actions

**Why it happens:**
Agents often treat negative feedback (e.g., "Nothing happens", "See nothing") as minor glitches rather than critical indicators that the current plan is invalid. In Trajectory 1, the agent repeatedly attempted to heat a mug with different appliances after receiving "Nothing happens" responses. In Trajectory 2, the agent opened numerous empty drawers without shifting its search strategy to other potential locations like countertops.

**How to avoid:**
1. Treat negative feedback as a signal to stop and analyze the current state.
2. Verify prerequisites (e.g., is the object actually in the container?) before acting.
3. Diversify search or interaction methods if the first attempt fails (e.g., check counters if drawers are empty).
