---
name: action-feedback-handling
description: Use when an action returns 'Nothing happened' to prevent infinite loops and pivot to alternative strategies.
category: general
---

## Action Feedback Handling

**Process:**
1. Execute the intended action (e.g., take, move, open).
2. Immediately read the observation response.
3. If response contains 'Nothing happened', abort the current action attempt.
4. Verify object location or switch to a different target/location.

**Anti-patterns:**
- Repeating the exact same action 2+ times after receiving 'Nothing happened'.
- Ignoring negative feedback and assuming the action succeeded silently.

**Failure Recovery:**
- If 'Nothing happened' persists, check if the object is already held or located elsewhere (e.g., move to a different surface).
- Switch interaction verbs (e.g., try 'move' instead of 'take') if applicable.
