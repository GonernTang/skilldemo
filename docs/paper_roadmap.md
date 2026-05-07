# qskill Paper Roadmap

> 日期：2026-05-07
> 状态：Draft

---

## 1. 核心贡献 Statement

### 推荐版本（候选 C）

> **We introduce qskill, a non-parametric skill evolution approach that decouples stable skill retention from plastic skill acquisition.** By combining Q-value guided retrieval, environment-driven skill value updates, and automatic skill culling/merging, qskill enables agents to continuously evolve their skill libraries without weight updates, effectively reconciling the stability-plasticity dilemma in lifelong learning scenarios.

### 备选版本

#### 候选 A（聚焦 Q-value 引导检索）

> **We propose qskill, a framework that introduces Q-value guided skill retrieval to dynamically balance semantic relevance and empirical utility.** Unlike existing methods that rely solely on semantic similarity, qskill maintains a lightweight skill library by continuously updating skill Q-values through environmental feedback and pruning low-value skills via a novel culling mechanism.

#### 候选 B（聚焦技能库维护）

> **We present a skill evolution framework that maintains a compact, high-performance skill library through value-driven culling and similarity-based merging.** Our approach addresses the non-stationary nature of skill utility by dynamically adjusting skill retention based on real-world task outcomes.

---

## 2. 核心机制实现状态

### 已实现

| 机制 | 文件 | 状态 |
|------|------|------|
| Skill Value (Q-value) 更新 | `skill.py` | ✅ `update_skill_value()` |
| Q-value 引导检索 | `batch_integration.py` | ✅ 混合评分 |
| Skill Culling | `batch_integration.py` | ✅ `_cull_low_value_skills()` |
| Skill Merging (发现阶段) | `batch_integration.py` | ✅ `_find_mergeable_skills()` |
| Skill Merging (合并执行) | - | ❌ 未实现 |

### Culling 逻辑

```
触发条件：技能总数 > max_skills 时，trigger_batch_extraction() 后自动触发

淘汰条件：
1. skill_value < cull_threshold (默认 0.3)
2. usage_count >= cull_min_usage (默认 3)

淘汰数量：每次最多 cull_batch_size 个 (默认 5)
```

### Merging 逻辑

```
触发条件：新技能提取后检查 enable_merging

合并逻辑：
1. 计算新技能 embedding (name + description)
2. 与已有技能计算 cosine similarity
3. similarity >= 0.85 的标记为可合并
4. 相关技能归组，返回待合并列表

注意：目前只发现可合并的组，实际 LLM 合并操作未实现
```

---

## 3. 下一步实验计划

### 优先级 1：消融实验

| 实验 | 对比条件 | 预期结果 |
|------|----------|----------|
| Q-value 有/无 | Q-value 随机 vs Q-value 学习 | Q-value 学习版本成功率 +X% |
| Culling 有/无 | 固定库大小 vs 动态淘汰 | 有 culling 在大数据集下更稳定 |
| Merging 有/无 | 有重复技能 vs 自动合并 | 合并后检索 precision 提升 |

### 优先级 2：Baseline 对比

| Baseline | 说明 | 预期差距 |
|----------|------|----------|
| MemRL (无 skill) | 纯 memory 增强 | +Y% |
| SkillRL | 无 Q-value，无 culling | +Z% |
| Random Retrieval | 随机选择技能 | 显著低于 Q-value 引导 |
| Semantic Only | 纯相似度检索 | 低于 hybrid 方式 |

### 优先级 3：多 Benchmark 验证

- [x] ALFWorld（已有基础）
- [ ] BigCodeBench
- [ ] HLE
- [ ] Lifelong Agent Bench

---

## 4. 待解决问题

| 问题 | 影响 | 建议 |
|------|------|------|
| Merging 实际执行未实现 | 无法验证合并效果 | 实现 LLM-based merge |
| 理论分析缺失 | 论文深度不足 | 添加 Q-value 收敛性证明 |
| 只在 ALFWorld 验证 | 泛化性存疑 | 扩展到其他 benchmark |

---

## 5. 参考论文 Contribution Statement

| 论文 | Contribution Statement | 值得学习的地方 |
|------|----------------------|----------------|
| Skill0 | "SKILL0 enables agents to internalize skills during training, achieving zero-shot execution without runtime retrieval" | 贡献清晰，实验扎实 |
| SkillMOO | "SkillMOO uses multi-objective optimization to evolve skill bundles, simultaneously maximizing success rate while minimizing cost" | 多目标框架，实验设计 |
| SRA | "SRA introduces dynamic skill retrieval from external libraries, addressing the skill incorporation gap" | Benchmark 设计 |

---

## 6. 论文大纲（初稿）

```
1. Introduction
   - Problem: AI agents struggle to self-evolve without expensive retraining
   - Insight: Decouple stable reasoning from plastic memory/skill
   - Contribution: qskill framework

2. Related Work
   - Self-evolving agents (MemRL, MemSkill, SkillRL, OpenCLAW-RL)
   - Skill-augmented LLM agents
   - Runtime memory and retrieval systems

3. Problem Formulation
   - Skill library as a Markov decision process
   - Q-value update as bandit problem

4. Method: qskill
   4.1 Skill Extraction (from trajectories)
   4.2 Q-value guided Retrieval
   4.3 Value-driven Culling
   4.4 Similarity-based Merging

5. Experiments
   5.1 Benchmarks (ALFWorld, BigCodeBench, HLE, LLB)
   5.2 Ablation studies
   5.3 Analysis (skill evolution over time)

6. Conclusion and Future Work
```

---

## 7. 时间线（建议）

| 阶段 | 任务 | 目标时间 |
|------|------|----------|
| Week 1 | 补足 4 benchmark 实验 | 5月中旬 |
| Week 2 | 消融实验 + 统计分析 | 5月中旬 |
| Week 3 | 实现 Merging 合并执行 | 5月下旬 |
| Week 4 | 理论分析初稿 | 5月下旬 |
| Week 5 | 论文写作 | 6月初 |
| Week 6 | 论文修改 + 提交 | 6月中 |
