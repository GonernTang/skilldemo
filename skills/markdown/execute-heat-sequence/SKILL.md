---
name: execute-heat-sequence
description: Use when you have located an object that requires heating and must complete the full workflow from placement to final destination.
category: alfworld/heat
---

## Execute Heat Sequence

**Process:**
1. Carry the target object to the heating appliance (e.g., microwave).
2. Open the appliance door if it is currently closed.
3. Put the object inside the appliance.
4. Issue the heat command targeting the object or appliance.
5. Once the heating process completes, take the object out of the appliance.
6. Navigate to the final receptacle and place the object there.

**Anti-patterns:**
- Attempting to heat an object without first placing it inside the appliance.
- Aborting the task immediately after locating the object without moving to the heating station.
- Placing the heated object directly into the final receptacle without retrieving it from the appliance first.

**Failure Recovery:**
- If heating returns "Nothing happens", verify the object is physically inside the appliance before retrying.
- If the appliance is closed during the heat attempt, open it explicitly before issuing the heat command.
