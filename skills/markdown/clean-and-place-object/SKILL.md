---
name: clean-and-place-object
description: Use when you need to clean an item found in the environment and then place it in a specific receptacle.
category: alfworld/clean
---

## Clean and Place Object

**Process:**
1. Pick up the target object from its current location to ensure it is in inventory.
2. Navigate to a valid cleaning surface such as a sinkbasin or bathtubbasin.
3. Execute the clean command specifying the object and the basin.
4. Navigate to the target receptacle where the object needs to be placed.
5. Move the cleaned object into the target receptacle.

**Anti-patterns:**
- Attempting to clean an object that is not currently held in inventory.
- Using non-cleaning surfaces like countertops or tables as the cleaning location.

**Failure Recovery:**
- If the clean action fails, verify the object is indeed dirty and the basin is functional.
- If unable to reach the basin, check for obstacles or closed doors blocking the path.
