# Experiment Plan: Layered Q-Value with Learning Reward

**Date**: 2026-05-27
**Target**: NeurIPS/ICML 2026

---

## Claims to Validate

| # | Claim | Metric | Pass Criterion |
|---|-------|--------|----------------|
| C1 | LQRL maintains higher Q-value entropy than baseline | Q-value entropy (bits) at task 100 | Entropy(LQRL) > Entropy(baseline) |
| C2 | LQRL has better retrieval diversity | Unique skills retrieved in top-5 over 100 tasks | >30% unique |
| C3 | r_learning > 0 skills succeed more on similar tasks | Success rate on tasks matching improved patterns | >baseline by 10% |

---

## Experimental Configurations

### Main Experiment: β Ablation

| Run | β | Description | Tasks | Seeds |
|-----|---|-------------|-------|-------|
| R1 | 0.0 | Baseline (Q-only) | 50 | 3 |
| R2 | 0.3 | Default LQRL | 50 | 3 |
| R3 | 0.5 | Strong layering | 50 | 3 |
| R4 | 1.0 | Learning-only | 50 | 3 |

**Benchmark**: BCB hard subset
**Total**: 600 tasks (4 configs × 50 tasks × 3 seeds)

### Secondary: Long-Run Stability

| Run | Description | Tasks | Seeds |
|-----|-------------|-------|-------|
| R5 | LQRL (β=0.3) extended | 200 | 2 |
| R6 | Baseline extended | 200 | 2 |

**Purpose**: Verify Q-value entropy doesn't collapse over time

---

## Metrics to Log

### Primary Metrics
- Q-value distribution (mean, std, entropy)
- Skill retrieval frequency (top-1, top-5)
- Task success rate (per 10-task window)

### Secondary Metrics
- r_learning value distribution
- Content length over time
- Skill culling events

### Logs to Save
- Per-task: Q-values, r_task, r_learning, retrieval set
- Per-run: final Q-value distribution, entropy, success rate

---

## Run Order

```
Phase 1: Quick sanity check
  └── R1 (β=0) vs R2 (β=0.3), 20 tasks, 1 seed

Phase 2: Full ablation
  └── R1-R4, 50 tasks, 3 seeds

Phase 3: Long-run validation
  └── R5-R6, 200 tasks, 2 seeds
```

---

## Decision Gates

| Gate | Condition | Action |
|------|-----------|--------|
| G1 | Sanity check fails (all Q < 0.1) | Debug Q-update implementation |
| G2 | β=0 beats β=0.3 on entropy | Drop LQRL, investigate |
| G3 | Entropy too high (>4 bits) | Check for skill proliferation |
| G4 | Success rate < 10% | Increase skill retrieval k |

---

## Compute Estimate

| Phase | Tasks | GPU Hours |
|-------|-------|-----------|
| Phase 1 | 40 | 0.5 |
| Phase 2 | 600 | 6 |
| Phase 3 | 800 | 8 |
| **Total** | **1440** | **~15 GPU hours** |

---

## Expected Outcomes

| Outcome | Interpretation | Next Action |
|---------|----------------|-------------|
| LQRL entropy > baseline | Layering helps | Proceed to paper |
| LQRL entropy ≈ baseline | Layering doesn't help | Try different r_learning metric |
| LQRL entropy < baseline | Layering hurts | Reconsider formula |
