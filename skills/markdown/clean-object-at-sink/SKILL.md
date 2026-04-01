---
name: clean-object-at-sink
description: Use when you have an object in your inventory and need to clean it using a sink basin or bathtub basin.
category: alfworld/clean
---

## Clean Object at Sink Basin

**Process:**
1. Verify the target object is currently in your inventory.
2. Navigate to a valid cleaning location identified as 'sinkbasin' or 'bathtubbasin'.
3. Execute the action 'clean [object] with [location]'.
4. Proceed to the final destination once cleaning is complete.

**Anti-patterns:**
- Attempting to clean an object without picking it up first.
- Using a countertop or cabinet as the cleaning location instead of a sinkbasin.

**Failure Recovery:**
- If the object is not in inventory, locate and pick it up before returning to the sink.
- If the location is invalid, search for another sinkbasin or bathtubbasin in the environment.
