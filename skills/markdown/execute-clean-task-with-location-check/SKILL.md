---
name: execute-clean-task-with-location-check
description: Use when completing a pick-clean-place task to ensure the agent navigates to the sink before cleaning and searches surfaces efficiently for the target object.
category: alfworld/clean
---

## Execute Clean Task With Location Check

**Process:**
1. Locate the target object by checking common surfaces like countertops or tables first.
2. Pick up the object once found.
3. Navigate to a sinkbasin before attempting any cleaning action.
4. Execute the clean command only after arriving at the sinkbasin.
5. Navigate to the final destination receptacle.
6. Place the cleaned object into the destination.

**Anti-patterns:**
- Attempting to clean an object while standing away from a sinkbasin, as the action will fail silently.
- Blindly opening all drawers and cabinets without prioritizing visible surfaces where objects are typically placed.
