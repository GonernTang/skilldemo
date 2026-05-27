# Paper Plan

**Title**: LQRL: Layered Q-Value with Learning Reward for Non-Parametric Skill Evolution
**One-sentence contribution**: We propose LQRL, a skill Q-value update rule that decomposes reward into task success and content improvement components, enabling skills to be rewarded for learning even when they fail at tasks.
**Venue**: NeurIPS
**Type**: Method + Empirical
**Date**: 2026-05-27
**Page budget**: 9 pages (main body to Conclusion end, excluding references & appendix)
**Section count**: 6

---

## Claims-Evidence Matrix

| Claim | Evidence | Status | Section |
|-------|----------|--------|---------|
| LQRL formula correctly decomposes task vs learning reward | Theoretical derivation, TD-error analysis | Supported | §3 |
| β=0.3 outperforms β=0 (baseline) on success rate | BCB β-ablation: 40%→60% on 5 tasks | Partial (small N) | §4.1 |
| LQRL maintains higher Q-value entropy than baseline | Q-value tracking over tasks | Needs measurement | §4.2 |
| Skills with r_learning>0 have higher subsequent success | Task-to-task correlation analysis | Needs experiment | §4.3 |
| LQRL works across multiple benchmarks (BCB, HLE, ALFWorld, LLB) | Multi-benchmark evaluation | Planned | §4.4 |

---

## Structure

### §0 Abstract
- **What we achieve**: LQRL enables non-parametric skills to learn from failure by decomposing Q-value updates into task reward and learning reward
- **Why it matters**: Skills that improve their content through failure feedback are currently penalized, creating a contradiction that hinders skill evolution
- **How we do it**: We add a learning reward channel (r_learning) evaluated by LLM, combined with task reward via a layering weight β
- **Evidence**: 40%→60% success rate improvement on BigCodeBench with β=0.3 vs β=0
- **Most remarkable result**: Skills can gain positive Q-value updates even from failed tasks when content improves
- **Estimated length**: 200 words
- **Self-contained check**: Yes — formulas and benchmark description make this understandable without the full paper

---

### §1 Introduction
- **Opening hook**: In non-parametric skill systems, skills evolve their content through experience. When a skill fails, we refine its content to avoid the failure next time — yet this improved skill is penalized with a lower Q-value.
- **Gap / challenge**: Standard Q-learning only rewards task success (r_task), not content improvement. This creates a fundamental contradiction: skills that learn from failure are less likely to be retrieved.
- **One-sentence contribution**: We propose LQRL, which decomposes skill Q-value updates into task reward and learning reward, allowing skills to be rewarded for improving their content even when they fail.
- **Approach overview**: LQRL introduces r_learning evaluated by LLM to assess whether skill content improved after a task. The Q-value update becomes: Q_new = Q_old + α×[(1-β)×r_task + β×r_learning]
- **Key questions**: (1) Does decomposing rewards improve skill evolution? (2) What is the optimal β? (3) Does r_learning correlate with future success?
- **Contributions**:
  1. First formal decomposition of task reward from learning reward in non-parametric skill Q-values
  2. LLM-based r_learning evaluation for automatic content improvement assessment
  3. Comprehensive evaluation across 4 benchmarks (BCB, HLE, ALFWorld, LLB) with β-ablation
- **Results preview**: β=0.3 improves success rate by 20 percentage points over baseline (β=0) on BigCodeBench
- **Hero figure**: Fig 1 should show: (left) the contradiction in standard Q-learning where failure→content_improvement→Q_decrease, (right) LQRL where failure→content_improvement→r_learning→Q_maintained/increased
- **Estimated length**: 1.5 pages
- **Key citations**: MemRL, MemSkill, EvoSkills, SkillClaw
- **Front-loading check**: Yes — the contradiction is clearly stated in opening paragraph

---

### §2 Related Work
- **Subtopics**:
  1. Non-parametric skill systems (MemRL, MemSkill, SkillClaw, EvoSkills)
  2. Q-value guided skill retrieval and selection
  3. Reward decomposition in RL (options framework, HER, hindsight experience replay)
- **Positioning**:
  - MemRL: Q-value metadata but no content evolution reward
  - EvoSkills: Content verification but no layered rewards
  - Options: Theoretical framework but no skill content evaluation
  - HER: Hindsight success re-labeling but not applicable to skill systems
- **Minimum length**: 1 page (3-4 paragraphs with synthesis)
- **Must NOT be just a list**: Compare assumptions and guarantees across systems

---

### §3 Method
- **Notation**:
  - Q(s): skill value
  - α: learning rate
  - β: layering weight
  - r_task: task success reward (+1 success, 0 failure)
  - r_learning: content improvement reward (+0.5 improved, -0.5 degraded, 0 unchanged)
- **Problem formulation**: Skill Q-value update in non-parametric systems
- **Method description**:
  1. After each task, evaluate content improvement via LLM judge
  2. Compute r_learning based on failure_scenario quality assessment
  3. Apply LQRL update formula
  4. Manage failure_scenario storage with quality thresholds and merge logic
- **Formal statements**: Theorem 1 (LQRL reduces Q-penalty for improving skills), Theorem 2 (β optimality bound)
- **Proof sketch locations**: §3.3 (main text), Appendix A (full proofs)
- **Estimated length**: 2 pages

---

### §4 Experiments
- **Figures planned**:
  - Fig 1 (Hero): System overview showing the Q-value update contradiction vs LQRL solution
  - Fig 2 (Bar chart): β-ablation results on BCB (β=0, 0.3, 0.5, 1.0)
  - Fig 3 (Line plot): Q-value entropy over tasks for β=0 vs β=0.3
  - Fig 4 (Bar chart): Multi-benchmark success rates comparison
  - Table 1: Main results — success rate by benchmark and β value
  - Table 2: Skill retrieval diversity metrics
- **Data source**: `test/bcb/test_results.json`, `refine-logs/FINAL_PROPOSAL.md`

#### §4.1 BigCodeBench Ablation
- β comparison: 0, 0.3, 0.5, 1.0
- Metric: success rate, Q-value entropy
- Expected: β=0.3 optimal (confirmed 40%→60% on 5-task sample)

#### §4.2 Q-Value Entropy Analysis
- Track Q-value distribution over training
- Metric: entropy of skill retrieval probabilities
- Expected: LQRL maintains higher entropy

#### §4.3 Multi-Benchmark Evaluation
- BCB (code generation)
- HLE (science questions)
- ALFWorld (physical manipulation)
- LLB (database/shell/kg queries)

#### §4.4 r_learning Correlation Analysis
- Post-hoc analysis: does r_learning>0 predict future success?
- Metric: correlation coefficient

---

### §5 Analysis / Discussion
- **When does LQRL help**: Tasks with recoverable failures (not random noise)
- **When does LQRL hurt**: Tasks where failure indicates fundamental unsuitability
- **β selection**: Theoretical bound and empirical validation
- **Limitations**:
  - r_learning depends on LLM judgment quality
  - Small-scale experiments (5-10 tasks per condition)
  - No theoretical convergence guarantee
- **Estimated length**: 1 page

---

### §6 Conclusion
- **Restatement**: LQRL enables skills to learn from failure by decomposing task and learning rewards
- **Limitations**: Small-scale validation, LLM-dependent r_learning
- **Future work**: (1) Theoretical convergence analysis, (2) Larger-scale ablation, (3) Learned r_learning
- **Estimated length**: 0.5 pages

---

## Figure Plan

| ID | Type | Description | Data Source | Priority |
|----|------|-------------|-------------|----------|
| Fig 1 | Hero/Architecture | System overview: Standard Q-learning vs LQRL comparison showing the contradiction and solution | manual (diagram) | HIGH |
| Fig 2 | Bar chart | β-ablation: Success rate vs β value (0, 0.3, 0.5, 1.0) on BCB | `test/bcb/test_results.json` | HIGH |
| Fig 3 | Line plot | Q-value entropy over task number for β=0 vs β=0.3 | `refine-logs/FINAL_PROPOSAL.md` | MEDIUM |
| Fig 4 | Bar chart | Multi-benchmark success rates: BCB, HLE, ALFWorld, LLB | Planned experiments | HIGH |
| Table 1 | Comparison table | Main results: success rate by benchmark × β | Planned | HIGH |
| Table 2 | Ablation table | Ablation of r_learning components | Planned | MEDIUM |

**Hero Figure (Fig 1) detailed description**:
- Left panel: "Standard Q-learning" — shows flow: Task Fail → Content Improve → Q decreases (annotated with Q_old - α×Q_old formula)
- Right panel: "LQRL" — shows flow: Task Fail → Content Improve → r_learning evaluated → Q maintained/increased (annotated with Q_old + α×[(1-β)×0 + β×0.5] formula)
- Visual: Use downward arrow (red) for standard Q-learning, upward arrow (green) for LQRL
- Comparison caption: "LQRL prevents content-improving skills from being penalized"

---

## Citation Plan

- §1 Intro: MemRL (Q-value metadata), SkillClaw (skill evolution)
- §2 Related: MemRL, EvoSkills, SkillClaw, SkillOS, SkillRouter
- §3 Method: MemRL (Q-learning baseline), Options framework (reward decomposition theory)
- §4 Experiments: BigCodeBench, HLE, ALFWorld, LLB benchmarks

---

## Reviewer Feedback

*To be completed after GPT-5.4 review*

---

## Next Steps
- [ ] /paper-figure to generate figures (Fig 2, Table 1 from existing results)
- [ ] /paper-write to draft LaTeX sections
- [ ] /paper-compile to build PDF
- [ ] Complete multi-benchmark experiments for Fig 4
