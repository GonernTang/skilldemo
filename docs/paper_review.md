# 论文评审意见：qskill - Self-Evolving Agents via Runtime RL on Episodic Memory

> 日期：2026-05-07
> 评审人：Claude

---

## 整体评价

你的工作有一定创新性，但目前处于"系统实现"阶段，距离论文发表还需要**显著的科研贡献提炼**。现有工作更像是一个"skill management系统"而不是"RL theory for skill evolution"。

---

## 优点

1. **工程实现扎实** - skill culling/merging 机制解决了一些实际问题
2. **与 MemRL 框架结合** - 提出了 memory + skill 协同的思路
3. **多类别技能** - general/task-specific/mistakes 分类合理

---

## 核心不足

### 1. 贡献点不够清晰

现有工作更像"实现了一个系统"而非"提出了新方法/理论"。论文需要回答：

- **你的核心 insight 是什么？** 为什么现有的 skill 方法不够好？
- **你证明了什么假设？** Q-value guided retrieval 相比随机/语义检索有多大提升？

### 2. 缺乏与前沿工作的差异化

| 论文 | 核心贡献 | 你的工作差异点 |
|------|----------|----------------|
| Skill0 | 训练时内化技能，零样本执行 | 你仍是运行时检索 |
| SkillMOO | 多目标优化 bundle | 你没有优化框架 |
| SSL | 结构化技能表示 | 你仍是 markdown 纯文本 |
| SRA | 外部 skill 库检索 | 你只是内部提取 |
| Memento | 可执行技能单元 | 你没有执行层 |

**你的独特贡献是什么？** 目前看起来是"把几个已有想法拼在一起"。

### 3. 实验验证不足

- 只在 ALFWorld 上验证？需要多 benchmark 对比
- **消融实验**：Q-value 真的有用吗？去掉会差多少？
- **与 baseline 对比**：vs 不加 skill、vs 随机检索、vs 纯语义检索
- **统计显著性**：多次运行的结果，不是单次跑分

### 4. Skill Culling/Merging 是小创新

坦率说，culling 和 merging 是工程 trick，不足以支撑论文。Reviewer 会问：

- 为什么不是让 LLM 直接决定保留哪些技能？
- 与 Knowledge Distillation/Debate 相比优势在哪？

---

## 建议的突破方向

### 方向 A：Skill Evolution Theory

不是做系统，而是提出**技能如何"正确"演化的理论**：

- 什么时候该创造新技能 vs 复用已有？
- 技能之间的层次关系如何涌现？
- 你的 3 种类别是最优的吗？

### 方向 B：Two-Phase Retrieval 的理论分析

你提到"两阶段检索过滤噪声"，但没有深入分析：

- 什么造成噪声？检索阶段 vs 排序阶段的噪声源不同
- 能否形式化证明两阶段优于单阶段？

### 方向 C：与 Skill0 的结合

他们做的是"训练时内化"，你做的是"运行时检索"——**两者可以正交结合**，这是有潜力的方向。

### 方向 D：Skill Value 的理论性质

你的 Q-value 更新机制是否收敛？能否证明？

- 这本质上是 bandit 问题，有现成的理论框架可以套用

---

## 下一步建议

1. **补足实验**：至少 4 个 benchmark + 消融 + 统计显著性
2. **提炼贡献**：明确 1-2 个核心 insight，不要只是"实现了 xxx 功能"
3. **对齐论文**：参考 Skill0/SkillMOO 的写作方式，突出 theoretical contribution
4. **考虑 arxiv 投稿**：先看能不能中，再论深度

---

## 坦率说

如果只是"实现了一个带 skill 的 MemRL"，现在发 paper 有点早。但如果能：

- 证明 Q-value guided retrieval 显著优于 baseline
- 提出技能演化机制的理论分析
- 在 4 个 benchmark 上全面超越现有方法

那就有竞争力了。

**现在最缺的是：一个能说服 reviewer 的核心贡献 statement。**

---

## 参考论文

1. **Skill0** (Lu et al., 浙大) - 训练时内化技能，零样本执行
2. **SkillMOO** (Gong et al.) - 多目标优化 coding agents
3. **SSL** (Qiliang et al.) - Scheduling-Structural-Logical 表示
4. **SRA** (Su et al.) - 外部 skill 库动态检索
5. **Memento** - 可执行技能单元结构
