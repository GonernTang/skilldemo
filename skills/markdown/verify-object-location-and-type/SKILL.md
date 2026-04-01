---
name: verify-object-location-and-type
description: Common mistake: Selecting or searching for objects without confirming they match the task requirements or exist in the expected location.
category: common_mistakes
---

## Do Not Assume Object Existence or Match

**Why it happens:**
Agents often default to searching standard containers (like drawers) or picking visually similar items (like a 'cup' instead of a 'mug') without explicitly verifying the object ID or location against the task goal. In Trajectory 1, the agent searched drawers sequentially for an AlarmClock despite seeing a bed in the initial scan. In Trajectory 2, the agent picked a 'cup' when the task required a 'mug', leading to invalid interactions.

**How to avoid:**
1. Cross-reference initial room observations with task requirements before starting the search path.
2. Explicitly verify the object name and ID upon discovery (e.g., confirm 'mug' vs 'cup') before attempting complex actions like heating or placing.
3. Expand search scope beyond single furniture types if the target is not found in the first few attempts.
