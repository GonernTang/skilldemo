# Final Proposal: Layered Q-Value with Learning Reward

**Date**: 2026-05-27
**Verdict**: READY

---

## Problem Anchor

In non-parametric skill evolution systems, skill Q-values are updated only on task success/failure, creating a contradiction: when a skill's content is refined via failure feedback, its Q-value decreases, making it less likely to be retrieved—even though the skill has become more knowledgeable.

---

## Final Method Thesis

We propose **Layered Q-Value with Learning Reward (LQRL)**: a skill Q-value update rule that decomposes the reward into task success (r_task) and content improvement (r_learning), allowing skills to be rewarded for learning even when they fail at tasks.

---

## Core Formula

```
Q_new = Q_old + α × [(1-β) × r_task + β × r_learning]
```

Where:
- **r_task**: Task success reward (+1 success, -1 failure)
- **r_learning**: Content improvement reward (+0.5 improved, -0.5 degraded, 0 if unchanged)
- **α**: Learning rate (default: 0.1)
- **β**: Layering weight (0.0 to 1.0, default: 0.3)

---

## r_learning Metric Definition

**r_learning** is evaluated by comparing skill content before and after a task:

| Condition | r_learning |
|----------|-----------|
| Content improved (failure cases reduced, patterns added) | +0.5 |
| Content degraded (contradictions introduced) | -0.5 |
| Content unchanged | 0 |

**Evaluation method**: LLM judge compares skill content pre/post task:
- Prompt: "Did the skill content improve, degrade, or stay the same after this task?"
- Improvement = reduction in failure patterns + addition of successful patterns
- Degradation = introduction of contradictions or removal of valid patterns

---

## Why This Design

1. **Decouples success from learning**: A skill can fail at a task but still improve its content
2. **Encourages exploration**: Skills are rewarded for attempting difficult tasks even if they fail
3. **Maintains Q-value informativeness**: High Q always means "effective skill" not just "lucky skill"
4. **Simple to implement**: Two-line change to existing Q-update rule

---

## Dominant Contribution

**First formal decomposition of task reward from learning reward in non-parametric skill Q-values.**

---

## Complexity Intentionally Rejected

| Rejected | Reason |
|----------|--------|
| Per-step Q-update | Too complex; task-level is sufficient |
| Learned r_learning | Circular; using LLM to evaluate LLM-guided skills |
| Multi-dimensional Q | Overkill; single scalar Q is interpretable |
| Cross-skill rewards | Out of scope; single-skill focus |

---

## Key Claims

1. **Claim 1**: LQRL maintains higher Q-value entropy than baseline Q-only over 100+ tasks
2. **Claim 2**: Skills with LQRL achieve higher retrieval diversity (retrieved skills are less dominated by recent successes)
3. **Claim 3**: r_learning > 0 skills have higher success rate on subsequent similar tasks

---

## Ablation Scope

| Ablation | Purpose | Scope |
|----------|--------|-------|
| β = 0 (baseline) | Verify layering helps | Required |
| β = 0.3 | Default setting | Required |
| β = 0.5 | Stronger layering | Required |
| β = 1.0 | Learning-only | Optional |

---

## Remaining Risks

| Risk | Mitigation |
|------|-----------|
| r_learning metric noisy | Use LLM judge with few-shot examples |
| β tuning needed | Full ablation curve published |
| Content bloat | Culling mechanism in parallel |

---

## Target Venue

**NeurIPS 2026 or ICML 2026** (agents/RL workshop track)
