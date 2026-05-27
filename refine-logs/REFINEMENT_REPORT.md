# Refinement Report: Layered Q-Value with Learning Reward

**Date**: 2026-05-27
**Iterations**: 1

---

## Refinement Path

### Initial Formulation
```
Q_new = Q_old + α × [r_task + β × r_learning]
```

### Refined Formulation
```
Q_new = Q_old + α × [(1-β) × r_task + β × r_learning]
```

**Change**: Normalized by (1-β) to ensure r_task contribution scales correctly when β increases.

### r_learning Definition

**Initial**: Ambiguous (how to measure "content improvement"?)

**Refined**: LLM-judged comparison of skill content pre/post task:
- +0.5 if content improved (fewer failure patterns, more success patterns)
- -0.5 if content degraded (contradictions introduced)
- 0 if unchanged

---

## Questions Addressed

| Question | Answer |
|----------|--------|
| How to measure r_learning? | LLM judge with few-shot examples |
| What should β be? | Full ablation: 0, 0.3, 0.5, 1.0 |
| What if β=0? | Baseline (standard Q-only) |
| What if β=1? | Learning-only (no task reward) |

---

## Complexity Rejected

| Complexity | Reason Rejected |
|------------|-----------------|
| Per-step Q-update | Task-level sufficient for skill evolution |
| Learned r_learning | Circular reasoning |
| Multi-dimensional Q | Interpretability loss |
| Cross-skill rewards | Out of scope |

---

## Final Method Summary

**Name**: LQRL (Layered Q-Value with Learning Reward)

**Core insight**: Decompose skill reward into task success and learning progress.

**Formula**: `Q_new = Q_old + α × [(1-β) × r_task + β × r_learning]`

**Claims**:
1. Higher Q-value entropy over time
2. Better retrieval diversity
3. Improved skill content quality
