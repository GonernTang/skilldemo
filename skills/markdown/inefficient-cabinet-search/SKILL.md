---
name: inefficient-cabinet-search
description: Common mistake: Exhaustively searching all numbered cabinets sequentially without prioritizing high-probability locations for the target object.
category: common_mistakes
---

## Inefficient Cabinet Search

**Why it happens:**
The agent defaults to a systematic scan of available numbered objects (cabinets 1-N) rather than utilizing semantic priors about where specific items (like food) are typically located.

**How to avoid:**
1. Prioritize search locations based on object category (e.g., check countertops and fridges for food items before checking storage cabinets).
2. Limit the number of locations checked per search phase to prevent excessive wandering and time consumption.
