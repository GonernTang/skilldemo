---
name: wrong-location-search
description: Agent searches containers when objects are on visible surfaces or searches wrong container type
category: common_mistakes
---

## Mistake Title

**Why it happens:**
In trajectory 3, the agent spent 20 steps opening cabinets 1-10 searching for PepperShaker, but the task requires placing on Shelf-20. The agent never checked visible surfaces where objects typically spawn, and never attempted to place anything on the target shelf. This pattern of exhaustive container searching without surface checks causes failure.

**How to avoid:**
1. First scan visible surfaces in the current room before opening containers
2. Verify the target receptacle type matches the task (shelf vs cabinet)
3. If searching containers yields nothing, expand search to other room areas rather than continuing same pattern
4. Track which locations have been checked to avoid redundant searches
