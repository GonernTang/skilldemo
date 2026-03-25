# Skill Layer Design Document

## 1. 概述

在现有的三层架构（Runner → Agent → MemoryService）基础上，新增 **Skill 层**，用于从任务轨迹中提取可复用的技能（Skill），并在后续任务执行时主动检索并注入相关 Skill 到模型上下文。

```
┌─────────────────────────────────────────────────────────┐
│                     Runner 层                            │
│         (编排整个训练/评估循环)                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │  ReAct 执行循环:                                   │  │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────────┐  │  │
│  │  │ Agent   │───▶│ 观察    │───▶│ Skill动态    │  │  │
│  │  │ 执行    │    │ 结果    │    │ 检索(可选)   │  │  │
│  │  └─────────┘    └─────────┘    └─────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Skill 层 (新增)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Skill提取器  │  │ Skill存储   │  │ Skill检索器      │  │
│  │ Extractor   │  │ Store      │  │ Retriever       │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                                                          │
│  特点: 可在 ReAct 循环中动态检索                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Agent 层                              │
│         (基于LLM的Agent，执行任务)                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                MemoryService 层                         │
│         (记忆的构建、检索、更新)                         │
└─────────────────────────────────────────────────────────┘
```

## 2. 核心功能

### 2.1 Skill 提取器 (Skill Extractor)

#### 2.1.1 核心设计思想

Skill Extractor 的核心任务是**从成功执行的任务轨迹中提炼出可复用的技能模式**。

**输入**: Agent 成功执行的任务轨迹 (Trajectory)
**输出**: 结构化的 Skill JSON

**关键挑战**:
1. 轨迹中可能包含大量上下文噪音，需要提取核心动作模式
2. 需要生成 `applicable_observations`（用于触发）和 `trigger_keywords`（用于检索）
3. 需要识别动作之间的因果关系（reasoning）

#### 2.1.2 LLM 提取流程

```
输入: 成功轨迹
         │
         ▼
┌─────────────────────────────────────────┐
│  Step 1: 轨迹解析                       │
│  - 提取 action-observation 对            │
│  - 识别任务类型 (task_type)              │
│  - 提取关键实体 (物品、位置)             │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Step 2: LLM 提炼 (核心)                │
│  - 识别核心动作步骤                       │
│  - 生成动作描述和 reasoning               │
│  - 生成触发关键词和适用观察               │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Step 3: 后处理                          │
│  - 过滤无效步骤                          │
│  - 合并相似步骤                          │
│  - 生成最终 Skill JSON                   │
└─────────────────────────────────────────┘
         │
         ▼
输出: Skill JSON
```

#### 2.1.3 SkillExtractor 实现

```python
class SkillExtractor:
    """从轨迹中提取 Skill 的提取器"""

    def __init__(
        self,
        llm: BaseLLM,
        embedder: BaseEmbedder = None,
        min_steps: int = 2,          # 最少步骤数
        max_steps: int = 10,         # 最多步骤数
        deduplicate_similar: bool = True,  # 是否去重相似步骤
    ):
        self.llm = llm
        self.embedder = embedder
        self.min_steps = min_steps
        self.max_steps = max_steps
        self.deduplicate_similar = deduplicate_similar

    def extract(
        self,
        trajectory: List[Dict],      # 消息格式轨迹
        task_description: str,
        task_type: str,
        source_trajectory_id: str = None,
    ) -> Optional[Skill]:
        """
        从成功轨迹中提取 Skill

        Args:
            trajectory: Agent 执行轨迹 (message list)
            task_description: 任务描述
            task_type: 任务类型
            source_trajectory_id: 源轨迹 ID

        Returns:
            提取的 Skill，或 None（如果提取失败）
        """

        # Step 1: 解析轨迹
        action_obs_pairs = self._parse_trajectory(trajectory)
        if len(action_obs_pairs) < self.min_steps:
            return None

        # Step 2: LLM 提炼
        extracted = self._llm_refine(
            action_obs_pairs=action_obs_pairs,
            task_description=task_description,
            task_type=task_type,
        )

        # Step 3: 后处理
        skill = self._post_process(
            extracted=extracted,
            task_description=task_description,
            task_type=task_type,
            source_trajectory_id=source_trajectory_id,
        )

        return skill

    def _parse_trajectory(
        self,
        trajectory: List[Dict]
    ) -> List[Dict[str, str]]:
        """
        解析轨迹，提取 action-observation 对

        输入格式:
        [
            {"role": "assistant", "content": "Thought: ...\nAction: go to refrigerator"},
            {"role": "user", "content": "Observation: You are in the kitchen..."},
            ...
        ]

        输出格式:
        [
            {"action": "go to refrigerator", "observation": "You are in the kitchen..."},
            ...
        ]
        """
        pairs = []
        current_action = None

        for msg in trajectory:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "assistant":
                # 提取 Action
                if "Action:" in content:
                    action = content.split("Action:")[-1].strip()
                    current_action = action
            elif role == "user" and content.startswith("Observation:") and current_action:
                # 提取 Observation
                observation = content.replace("Observation:", "").strip()
                pairs.append({
                    "action": current_action,
                    "observation": observation
                })
                current_action = None

        return pairs

    def _llm_refine(
        self,
        action_obs_pairs: List[Dict[str, str]],
        task_description: str,
        task_type: str,
    ) -> Dict:
        """
        使用 LLM 从 action-observation 对中提炼 Skill 信息

        LLM 会:
        1. 识别核心动作步骤
        2. 为每步生成 reasoning
        3. 生成适用观察条件
        4. 生成触发关键词
        """

        # 格式化 action-observation 对
        steps_text = "\n".join([
            f"Step {i+1}:\n  Action: {p['action']}\n  Observation: {p['observation']}"
            for i, p in enumerate(action_obs_pairs)
        ])

        prompt = f"""你是一个任务分解专家。请从以下成功执行的轨迹中提取可复用的技能模式。

## 任务描述
{task_description}

## 任务类型
{task_type}

## 执行轨迹
{steps_text}

## 你的任务
1. 分析这个轨迹，识别核心的动作步骤（可能需要过滤一些噪音步骤）
2. 为每个核心步骤生成:
   - action: 原始动作
   - observation_pattern: 触发此动作的观察条件（简洁描述）
   - reasoning: 为什么要执行这个动作
3. 生成技能的元信息:
   - name: 技能名称（简洁，描述技能做什么）
   - description: 技能描述（描述功能和使用场景，2-3句话）
   - trigger_keywords: 触发关键词列表（5-10个，用于检索）
   - applicable_observations: 适用观察条件列表（3-5个）
4. 判断 skill_type:
   - "primitive": 单一技能，不可再分
   - "composite": 组合技能，可由多个子技能组成

## 输出格式 (JSON)
{{
  "name": "技能名称",
  "description": "技能描述",
  "trigger_keywords": ["关键词1", "关键词2", ...],
  "applicable_observations": ["观察1", "观察2", ...],
  "skill_type": "primitive 或 composite",
  "steps": [
    {{
      "action": "原始动作",
      "observation_pattern": "触发条件",
      "reasoning": "动作原因"
    }},
    ...
  ]
}}

请仅输出 JSON，不要有其他内容。
"""

        response = self.llm.generate([
            {"role": "user", "content": prompt}
        ])

        # 解析 JSON 响应
        import json
        try:
            extracted = json.loads(response)
            return extracted
        except json.JSONDecodeError:
            return None

    def _post_process(
        self,
        extracted: Dict,
        task_description: str,
        task_type: str,
        source_trajectory_id: str,
    ) -> Skill:
        """后处理，生成最终 Skill 对象"""

        import hashlib
        import time
        skill_id = f"skill_{int(time.time())}_{hashlib.md5(task_description.encode()).hexdigest()[:8]}"

        steps = []
        for step_data in extracted.get("steps", []):
            steps.append(SkillStep(
                action=step_data.get("action", ""),
                observation_pattern=step_data.get("observation_pattern", ""),
                reasoning=step_data.get("reasoning", ""),
            ))

        return Skill(
            skill_id=skill_id,
            name=extracted.get("name", task_description[:50]),
            description=extracted.get("description", task_description),
            task_type=task_type,
            trigger_keywords=extracted.get("trigger_keywords", []),
            applicable_observations=extracted.get("applicable_observations", []),
            steps=steps,
            skill_type=extracted.get("skill_type", "primitive"),
            parent_skill_id=None,
            success_rate=1.0,
            usage_count=0,
            last_used_at=None,
            created_at=datetime.now().isoformat(),
            source_trajectory_id=source_trajectory_id,
        )
```

#### 2.1.4 批量提取

当某个 Task Type 的成功率超过阈值时，批量从多个成功轨迹中提取 Skill：

```python
def batch_extract(
    self,
    trajectories: List[Tuple[List[Dict], str, str]],
    success_threshold: float = 0.7,
) -> List[Skill]:
    """
    批量提取 Skills

    适用于当某个 Task Type 积累了一定数量的成功轨迹后，
    可以综合多个轨迹提炼出更通用的 Skill
    """

    # 按 task_type 分组
    from collections import defaultdict
    grouped = defaultdict(list)
    for traj, desc, ttype in trajectories:
        grouped[ttype].append((traj, desc))

    all_skills = []

    for task_type, items in grouped.items():
        if len(items) < 3:
            continue

        # 合并多个轨迹，提炼通用模式
        merged_skill = self._merge_trajectories(
            trajectories=[t[0] for t in items],
            task_description=items[0][1],
            task_type=task_type,
        )
        if merged_skill:
            all_skills.append(merged_skill)

    return all_skills

def _merge_trajectories(
    self,
    trajectories: List[List[Dict]],
    task_description: str,
    task_type: str,
) -> Optional[Skill]:
    """
    合并多个相似轨迹，提炼通用技能模式
    """

    trajectories_text = ""
    for i, traj in enumerate(trajectories):
        pairs = self._parse_trajectory(traj)
        trajectories_text += f"\n轨迹 {i+1}:\n"
        for p in pairs:
            trajectories_text += f"  - Action: {p['action']}, Obs: {p['observation'][:50]}...\n"

    prompt = f"""你是一个任务分解专家。请分析以下多个相似的成功轨迹，找出它们的共同模式，提炼出一个可复用的通用技能。

## 任务描述
{task_description}

## 任务类型
{task_type}

## 多个成功轨迹
{trajectories_text}

## 你的任务
1. 分析这些轨迹的共同模式
2. 提炼出适用于所有轨迹的核心动作步骤
3. 生成一个通用的、可复用的技能

## 输出格式 (JSON)
{{
  "name": "通用技能名称",
  "description": "通用技能描述",
  "trigger_keywords": ["关键词1", "关键词2", ...],
  "applicable_observations": ["观察1", "观察2", ...],
  "skill_type": "primitive 或 composite",
  "steps": [
    {{
      "action": "通用动作（抽象后的）",
      "observation_pattern": "触发条件",
      "reasoning": "动作原因"
    }},
    ...
  ]
}}

请仅输出 JSON，不要有其他内容。
"""

    response = self.llm.generate([{"role": "user", "content": prompt}])

    # 解析并构建 Skill...
```

#### 2.1.5 提取触发条件

```python
class SkillExtractorIntegration:

    def should_extract(
        self,
        task_type: str,
        trajectory: List[Dict],
        success: bool,
        current_success_rate: float,
    ) -> Tuple[bool, str]:
        """
        判断是否应该提取或更新 Skill

        Returns:
            (should_act, action_type)
            action_type: "extract_new" | "update_existing" | "analyze_failure" | "none"
        """

        if not self.config.auto_extract:
            return False, "none"

        # 成功轨迹：提取新技能
        if success and self._has_enough_steps(trajectory):
            return True, "extract_new"

        # 批量提取：当某 task_type 成功率达到阈值
        if success and current_success_rate >= self.config.extract_threshold:
            return True, "extract_new"

        # 失败轨迹：分析失败原因
        if not success and self._has_enough_steps(trajectory):
            return True, "analyze_failure"

        return False, "none"

    def _has_enough_steps(self, trajectory: List[Dict]) -> bool:
        action_count = sum(
            1 for msg in trajectory
            if msg.get("role") == "assistant" and "Action:" in msg.get("content", "")
        )
        return action_count >= self.min_steps
```

#### 2.1.6 失败轨迹分析

失败轨迹同样重要，需要分析失败原因并用于：
1. **生成警示性 Skill**: 从失败轨迹中学习"什么不该做"
2. **更新现有 Skill**: 根据失败原因修改已有技能的适用条件

```python
class FailureAnalyzer:
    """分析失败轨迹，生成教训或更新现有技能"""

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def analyze_and_update(
        self,
        failed_trajectory: List[Dict],
        task_description: str,
        task_type: str,
        existing_skills: List[Skill],
    ) -> List[SkillUpdate]:
        """
        分析失败轨迹，返回对现有技能的更新

        Returns:
            List[SkillUpdate]: 需要对哪些 Skill 进行什么更新
        """

        # Step 1: 分析失败原因
        failure_analysis = self._analyze_failure(
            trajectory=failed_trajectory,
            task_description=task_description,
            task_type=task_type,
        )

        updates = []

        # Step 2: 为每个相关 Skill 生成更新
        for skill in existing_skills:
            if self._is_related_skill(skill, failure_analysis):
                update = self._generate_skill_update(
                    skill=skill,
                    failure_analysis=failure_analysis,
                )
                if update:
                    updates.append(update)

        return updates

    def _analyze_failure(
        self,
        trajectory: List[Dict],
        task_description: str,
        task_type: str,
    ) -> Dict:
        """
        使用 LLM 分析失败轨迹，找出失败原因
        """

        # 解析轨迹
        pairs = self._parse_trajectory(trajectory)

        # 找到失败点（最后观察）
        failure_point = pairs[-1] if pairs else None

        prompt = f"""你是一个失败分析专家。请分析以下失败轨迹，找出失败原因。

## 任务描述
{task_description}

## 任务类型
{task_type}

## 执行轨迹
{self._format_pairs(pairs)}

## 失败点
{failure_point}

## 你的任务
1. 分析在哪个步骤出了问题
2. 分析失败原因（是动作错误、顺序错误、还是前提条件不满足）
3. 识别导致失败的关键词或观察条件
4. 总结教训：以后遇到类似情况应该怎么做

## 输出格式 (JSON)
{{
  "failure_step": 失败的步骤索引,
  "failure_action": "失败的动作",
  "failure_reason": "失败原因分类 (wrong_action | wrong_order | missing_prerequisite | environment_error)",
  "failure_detail": "详细描述",
  "lesson": "教训总结（以后应该怎么做）",
  "avoid_keywords": ["应该避免的关键词1", "应该避免的关键词2"],
  "correct_approach": "正确的做法应该是什么"
}}

请仅输出 JSON。
"""

        response = self.llm.generate([{"role": "user", "content": prompt}])

        import json
        try:
            return json.loads(response)
        except:
            return None

    def _generate_skill_update(
        self,
        skill: Skill,
        failure_analysis: Dict,
    ) -> SkillUpdate:
        """
        根据失败分析生成对现有 Skill 的更新
        """

        update_type = self._determine_update_type(skill, failure_analysis)

        if update_type == "add_constraint":
            # 添加新的约束条件
            return SkillUpdate(
                skill_id=skill.skill_id,
                update_type="add_constraint",
                new_constraints=[failure_analysis.get("failure_detail", "")],
                warning=f"注意：{failure_analysis.get('lesson', '')}",
            )

        elif update_type == "mark_failure_scenario":
            # 标记为失败场景
            return SkillUpdate(
                skill_id=skill.skill_id,
                update_type="add_failure_scenario",
                failure_scenario={
                    "task_type": failure_analysis.get("failure_reason"),
                    "description": failure_analysis.get("failure_detail"),
                    "lesson": failure_analysis.get("lesson"),
                },
            )

        elif update_type == "create_antipattern":
            # 创建反向模式（什么不该做）
            return SkillUpdate(
                skill_id=skill.skill_id,
                update_type="create_antipattern",
                antipattern={
                    "action": failure_analysis.get("failure_action"),
                    "wrong_reason": failure_analysis.get("failure_detail"),
                    "correct_approach": failure_analysis.get("correct_approach"),
                },
            )

        return None

    def _determine_update_type(
        self,
        skill: Skill,
        failure_analysis: Dict,
    ) -> str:
        """
        判断应该对 Skill 进行什么类型的更新
        """

        reason = failure_analysis.get("failure_reason", "")

        if reason == "missing_prerequisite":
            return "add_constraint"
        elif reason == "wrong_action":
            return "create_antipattern"
        else:
            return "mark_failure_scenario"
```

#### 2.1.7 Skill 更新操作类型

当失败轨迹分析完成后，可能对现有 Skill 进行以下更新：

| 更新类型 | 说明 | 影响 |
|---------|------|------|
| **add_constraint** | 添加新的约束条件 | 限制 Skill 的适用范围 |
| **add_failure_scenario** | 添加失败场景 | 标记在哪些情况下不应使用 |
| **create_antipattern** | 创建反向模式 | 明确什么是不该做的 |
| **deprecate** | 废弃技能 | 当 Skill 持续失败时标记为废弃 |
| **merge** | 合并技能 | 将多个相似失败场景合并分析 |

```python
class SkillUpdate:
    """Skill 更新操作"""

    skill_id: str
    update_type: str  # "add_constraint" | "add_failure_scenario" | "create_antipattern" | "deprecate" | "merge"
    new_constraints: List[str] = []           # 新增约束
    warning: str = ""                          # 警告信息
    failure_scenario: Dict = None              # 失败场景
    antipattern: Dict = None                   # 反向模式
    deprecated: bool = False                   # 是否废弃
```

#### 2.1.8 完整提取/更新流程

```
任务完成 (成功/失败)
         │
         ▼
┌─────────────────────────────────────────┐
│  判断触发条件                             │
│  - 成功轨迹 + 足够步骤 → 提取新技能     │
│  - 失败轨迹 + 足够步骤 → 分析失败        │
│  - 成功率达标 → 批量提取/合并            │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  成功轨迹处理                             │
│  ┌─────────────────────────────────────┐│
│  │ 1. 解析 action-observation 对        ││
│  │ 2. LLM 提炼核心步骤                  ││
│  │ 3. 生成 trigger_keywords             ││
│  │ 4. 构建新 Skill                      ││
│  │ 5. 保存到存储                        ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  失败轨迹处理                             │
│  ┌─────────────────────────────────────┐│
│  │ 1. 解析轨迹                          ││
│  │ 2. LLM 分析失败原因                  ││
│  │ 3. 查找相关的现有 Skills              ││
│  │ 4. 生成 SkillUpdate                  ││
│  │ 5. 更新存储中的 Skills                ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

#### 2.1.9 完整 Skill 数据模型

```python
@dataclass
class SkillStep:
    """Skill 中的单个步骤"""
    action: str                           # 动作
    observation_pattern: str             # 触发此动作的观察条件
    reasoning: str                       # 为什么要执行这个动作


@dataclass
class Skill:
    """完整的 Skill 数据结构"""
    skill_id: str                         # 唯一标识
    name: str                            # 技能名称
    description: str                     # 技能描述
    task_type: str                       # 任务类型
    trigger_keywords: List[str]          # 触发检索关键词
    applicable_observations: List[str]   # 适用观察条件
    steps: List[SkillStep]              # 执行步骤
    skill_type: str = "primitive"       # primitive | composite

    # 层级关系
    parent_skill_id: Optional[str] = None  # 父技能 ID（composite skill 时）

    # 统计信息
    success_rate: float = 1.0           # 成功率
    usage_count: int = 0                # 使用次数
    last_used_at: Optional[str] = None  # 最后使用时间
    created_at: str = ""                 # 创建时间
    source_trajectory_id: Optional[str] = None  # 源轨迹 ID

    # 失败相关（新增）
    failure_scenarios: List[Dict] = field(default_factory=list)  # 失败场景列表
    antipatterns: List[Dict] = field(default_factory=list)      # 反向模式列表
    constraints: List[str] = field(default_factory=list)        # 约束条件
    deprecated: bool = False            # 是否废弃


# Skill JSON 完整格式示例
{
  "skill_id": "skill_001",
  "name": "打开冰箱并取出物品",
  "description": "描述技能的功能和适用场景",
  "task_type": "alfworld/pick_and_place",
  "trigger_keywords": ["冰箱", "refrigerator", "取物品"],
  "applicable_observations": ["物品在冰箱里", "需要打开冰箱"],
  "steps": [
    {
      "action": "go to refrigerator",
      "observation_pattern": "在厨房能看到冰箱",
      "reasoning": "需要先移动到冰箱位置"
    }
  ],
  "skill_type": "primitive",
  "parent_skill_id": null,

  # 统计
  "success_rate": 0.85,
  "usage_count": 10,
  "last_used_at": "2026-03-25T10:00:00",
  "created_at": "2026-03-20T10:00:00",
  "source_trajectory_id": "mem_xxx",

  # 失败相关
  "failure_scenarios": [
    {
      "task_type": "wrong_action",
      "description": "如果物品不在冰箱而是在柜子里，会导致失败",
      "lesson": "先确认物品实际位置再执行动作"
    }
  ],
  "antipatterns": [
    {
      "action": "open fridge before go to refrigerator",
      "wrong_reason": "在移动到冰箱前就尝试打开它",
      "correct_approach": "先 go to refrigerator 再 open"
    }
  ],
  "constraints": [
    "确保目标物品确实在冰箱里",
    "确保冰箱门可以正常打开"
  ],
  "deprecated": false
}
```

### 2.2 Skill 存储 (Skill Storage)

**存储位置**: 本地 JSON 文件
**目录结构**:
```
skills/
├── index.json              # Skill 索引（快速检索）
├── skill_001.json          # 单个 Skill 文件
├── skill_002.json
└── ...
```

**索引结构** (index.json):
```json
{
  "skills": [
    {
      "skill_id": "skill_001",
      "name": "...",
      "task_type": "alfworld/pick_heat_then_place",
      "keywords": ["冰箱", "微波炉", "加热"],
      "file_path": "skill_001.json"
    }
  ],
  "total_count": 10
}
```

### 2.3 Skill 检索器 (Skill Retrieval)

#### 2.3.1 检索模式

Skill 检索器支持**四种检索模式**：

| 检索模式 | 匹配方式 | 优点 | 缺点 |
|---------|---------|------|------|
| **关键词检索** | 关键词重叠度 | 快速、简单 | 无法语义理解 |
| **任务类型检索** | 精确/前缀匹配 | 精确限定 | 覆盖率低 |
| **向量检索** | 语义相似度 | 泛化能力强 | 需要 embedding 模型 |
| **纯LLM推理** | LLM 自己判断 | 最智能、可理解复杂场景 | 需要额外 LLM 调用 |

#### 2.3.2 纯 LLM 推理检索模式

参考 Claude Code 的 Skill 使用方式，采用**纯 LLM 推理**进行 Skill 选择：

**核心思想**: 不使用算法匹配、向量嵌入或分类器，而是将所有可用 Skills 的元数据以格式化列表形式提供给 LLM，让 LLM 根据 description 中的关键词和使用场景描述，自主判断哪些 Skill 与当前任务相关。

**调用流程**:

```
┌─────────────────────────────────────────────────────────┐
│  1. 搜索匹配 (LLM 自主判断)                             │
│  ┌─────────────────────────────────────────────────────┐│
│  │ LLM 接收格式化 Skills 列表                          ││
│  │ → 回顾所有 Skills 的元数据和描述                    ││
│  │ → 判断哪些技能与当前任务/观察相关                   ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  2. 加载技能说明                                        │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 若匹配到某技能，LLM 使用 bash 读取 skill 目录下的   ││
│  │ SKILL.md，获取该技能的详细说明                       ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  3. 执行内部流程                                        │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 根据 SKILL.md 的说明，LLM:                           ││
│  │ → 按需读取额外的文档                                 ││
│  │ → 运行代码脚本                                      ││
│  │ → 执行具体操作                                      ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  4. 串联复用                                           │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 如果任务需要多个技能协作，LLM 依序调用它们:          ││
│  │ skill_a → skill_b → skill_c → ...                  ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**LLM 检索 Prompt 设计**:

```python
SYSTEM_PROMPT = """你是一个任务执行助手，擅长根据任务描述匹配并使用相关技能(Skill)。

## 可用技能列表
以下是系统中所有可用的技能，以 JSON 格式提供：

{skills_list}

## 任务
当前任务描述: {task_description}
当前观察: {observation}

## 你的任务
1. 仔细阅读所有可用技能
2. 判断哪些技能与当前任务相关（可以根据 description、trigger_keywords、applicable_observations 判断）
3. 列出所有你认为相关的技能 ID

## 输出格式
如果找到相关技能:
```
相关技能: skill_id_1, skill_id_2, ...
```
如果没有任何技能相关:
```
相关技能: None
```
"""

def retrieve_with_llm(
    task_description: str,
    observation: str,
    skills: List[Skill],
    llm: BaseLLM,
) -> List[str]:
    """使用 LLM 推理进行 Skill 检索"""

    # 1. 格式化 Skills 列表
    skills_list = "\n".join([
        f"- skill_id: {s.skill_id}"
        f"  name: {s.name}"
        f"  description: {s.description}"
        f"  task_type: {s.task_type}"
        f"  trigger_keywords: {s.trigger_keywords}"
        f"  applicable_observations: {s.applicable_observations}"
        for s in skills
    ])

    # 2. 构建 Prompt
    prompt = SYSTEM_PROMPT.format(
        skills_list=skills_list,
        task_description=task_description,
        observation=observation
    )

    # 3. 调用 LLM
    response = llm.generate([{"role": "user", "content": prompt}])

    # 4. 解析响应，提取匹配的 skill_ids
    matched_ids = parse_skill_ids_from_response(response)
    return matched_ids


def parse_skill_ids_from_response(response: str) -> List[str]:
    """从 LLM 响应中解析出匹配的 skill_ids"""
    import re
    match = re.search(r'相关技能:\s*(.+)', response)
    if match:
        ids_str = match.group(1).strip()
        if ids_str == "None":
            return []
        return [id.strip() for id in ids_str.split(",")]
    return []
```

**LLM 检索 vs 算法检索对比**:

| 维度 | 算法检索 | 纯 LLM 推理检索 |
|------|---------|----------------|
| 匹配能力 | 基于统计/规则 | 理解语义和意图 |
| 复杂场景 | 难以处理 | 可处理模糊/复杂描述 |
| 多技能组合 | 需要预设逻辑 | LLM 自动串联 |
| 速度 | 快 | 较慢（需要 LLM 调用） |
| 成本 | 无额外成本 | 有 LLM 调用成本 |

#### 2.3.3 推荐：混合模式

结合两种模式的优点：

```python
def retrieve_hybrid(
    task_description: str,
    observation: str,
    skills: List[Skill],
    llm: BaseLLM,
    embedder: BaseEmbedder,
    use_llm_fallback: bool = True,
) -> List[Skill]:
    """
    混合检索模式:
    1. 先用算法快速筛选候选集
    2. 再用 LLM 精排
    """

    # Step 1: 算法快速筛选 (top 20)
    candidates = algorithm_retrieve(
        query=task_description,
        observation=observation,
        skills=skills,
        k=20
    )

    # Step 2: LLM 精排 (从 20 个中选 5 个)
    if use_llm_fallback and len(candidates) > 5:
        matched_ids = retrieve_with_llm(
            task_description=task_description,
            observation=observation,
            skills=candidates,
            llm=llm
        )
        return [s for s in candidates if s.skill_id in matched_ids][:5]

    return candidates[:5]
```

#### 2.3.4 SkillRetriever 实现（保留算法模式）

```python
class SkillRetriever:
    """Skill 检索器，支持多种检索模式"""

    def __init__(
        self,
        skill_store: SkillStore,      # 存储后端
        embedder: BaseEmbedder,       # 向量嵌入器
        index_path: str = "skills/index.json"
    ):
        self.skill_store = skill_store
        self.embedder = embedder
        self.index = self._load_index(index_path)

    def retrieve(
        self,
        query: str = None,           # 任务描述或当前观察
        task_type: str = None,       # 任务类型
        observation: str = None,      # 当前观察（用于动态检索）
        k: int = 3,
        use_vector: bool = True,
        use_keyword: bool = True,
    ) -> List[Skill]:
        """
        检索相关 Skills

        Args:
            query: 任务描述或当前观察
            task_type: 任务类型 (e.g., "alfworld/pick_heat_then_place")
            observation: 当前观察 (用于 ReAct 循环中动态检索)
            k: 返回数量
            use_vector: 是否使用向量检索
            use_keyword: 是否使用关键词检索
        """

        # 1. 加载所有候选 Skills
        candidates = self._load_candidates(task_type)

        # 2. 计算各维度的匹配分数
        scores = []
        for skill in candidates:
            score = self._compute_score(
                skill=skill,
                query=query,
                observation=observation,
                task_type=task_type,
                use_vector=use_vector,
                use_keyword=use_keyword,
            )
            scores.append((skill, score))

        # 3. 按分数排序并返回 Top-K
        scores.sort(key=lambda x: x[1], reverse=True)
        return [skill for skill, _ in scores[:k]]

    def _compute_score(
        self,
        skill: Skill,
        query: str,
        observation: str,
        task_type: str,
        use_vector: bool,
        use_keyword: bool,
    ) -> float:
        """
        计算 Skill 与查询的匹配分数

        分数 = keyword_score * w1 + task_type_score * w2 + vector_score * w3
        """

        total_score = 0.0
        weights = []

        # 关键词分数
        if use_keyword and query:
            keyword_score = self._keyword_match(skill, query)
            total_score += keyword_score * 0.3
            weights.append(0.3)

        # 任务类型分数 (精确匹配权重最高)
        if task_type:
            task_type_score = self._task_type_match(skill, task_type)
            total_score += task_type_score * 0.4
            weights.append(0.4)

        # 向量相似度分数
        if use_vector and query:
            vector_score = self._vector_similarity(
                skill.description,
                query
            )
            total_score += vector_score * 0.3
            weights.append(0.3)

        # 归一化
        if weights:
            return total_score / sum(weights)
        return 0.0

    def _keyword_match(self, skill: Skill, query: str) -> float:
        """计算关键词匹配分数"""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        skill_keywords = set(k.lower() for k in skill.trigger_keywords)
        intersection = query_words & skill_keywords

        if not skill_keywords:
            return 0.0
        return len(intersection) / len(skill_keywords)

    def _task_type_match(self, skill: Skill, task_type: str) -> float:
        """计算任务类型匹配分数"""
        if not skill.task_type:
            return 0.0
        # 精确匹配
        if skill.task_type == task_type:
            return 1.0
        # 前缀匹配
        if task_type.startswith(skill.task_type) or \
           skill.task_type.startswith(task_type):
            return 0.8
        return 0.0

    def _vector_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的向量相似度 (cosine)"""
        emb1 = self.embedder.embed([text1])[0]
        emb2 = self.embedder.embed([text2])[0]
        dot = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(a * a for a in emb2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def retrieve_for_observation(
        self,
        observation: str,
        task_context: str = None,
        k: int = 2
    ) -> List[Skill]:
        """根据当前观察检索适用的 Skills (用于 ReAct 动态检索)"""
        candidates = self._load_candidates()
        matched = []

        for skill in candidates:
            if self._observation_matches(observation, skill):
                score = self._compute_observation_score(observation, skill)
                matched.append((skill, score))

        matched.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in matched[:k]]

    def _observation_matches(self, observation: str, skill: Skill) -> bool:
        """检查 observation 是否匹配 skill 的适用条件"""
        obs_lower = observation.lower()
        # 关键词匹配
        for keyword in skill.trigger_keywords:
            if keyword.lower() in obs_lower:
                return True
        # 观察模式匹配
        for pattern in skill.applicable_observations:
            if pattern.lower() in obs_lower:
                return True
        return False
```

#### 2.3.5 检索配置

```yaml
skill:
  retrieval:
    method: "hybrid"        # keyword | vector | hybrid
    weights:
      keyword: 0.3
      task_type: 0.4
      vector: 0.3
    vector_threshold: 0.6   # 向量检索相似度阈值
    keyword_threshold: 0.2  # 关键词匹配阈值
    diversity_filter: true  # 是否启用多样性过滤
    max_per_type: 2         # 每种 task_type 最多返回数量
```

### 2.4 Skill 注入 (Skill Injection)

**注入位置**: Agent 的 `_construct_messages()` 方法
**注入方式**: 作为系统提示的一部分，告知模型可以使用的相关 Skill

## 3. 项目运行流程（加入 Skill 层后）

### 3.1 核心设计：多轮 Skill 调用

**重要**: ReAct 框架下 Agent 可能**多次调用** Skill，而不仅在任务开始时注入一次。例如：

1. 任务 "把冰箱里的番茄加热后放到柜子里"
2. Agent 第一轮可能调用 `skill_001: 打开冰箱取物品`
3. Agent 第二轮可能调用 `skill_002: 加热物品`
4. Agent 第三轮可能调用 `skill_003: 放置物品到目标位置`

因此 Skill 检索应该是**动态的**，贯穿整个 ReAct 执行循环。

### 3.2 训练阶段流程

```
1. 任务开始
   ↓
2. [Skill 检索] 根据任务描述检索初始相关 Skills
   ↓
3. [Memory 检索] 根据任务描述检索相关 Memories
   ↓
4. [Prompt 构建] 将 Skills + Memories + Few-shot Examples 注入上下文
   ↓
5. ReAct 执行循环:
   ┌─────────────────────────────────────────┐
   │  for step in range(max_steps):          │
   │    ↓                                    │
   │    Agent 生成 Action                     │
   │    ↓                                    │
   │    环境返回 Observation                  │
   │    ↓                                    │
   │    [Skill 动态检索] ← 可选触发            │
   │    根据当前 Observation 判断是否需要      │
   │    检索新的相关 Skill                    │
   │    ↓                                    │
   │    如果需要新 Skill:                     │
   │      检索 → 追加到上下文                │
   └─────────────────────────────────────────┘
   ↓
6. 任务完成（成功/失败）
   ↓
7a. 如果成功:
    ├── [Skill 提取] 从轨迹中提取/更新 Skill
    ├── [Skill 存储] 保存到本地 JSON
    ├── [Memory 存储] 调用 MemoryService.add_memories()
    └── [Q-Value 更新] 调用 MemoryService.update_values()

7b. 如果失败:
    └── [Memory 更新] 调用 MemoryService.update_values()
```

### 3.3 推理阶段流程（使用 Skill）

```
1. 任务开始
   ↓
2. [Skill 检索] 初始检索相关 Skills
   ↓
3. [Memory 检索] 根据任务描述检索相关 Memories（可选）
   ↓
4. [Prompt 构建] 将 Skills + Memories + Few-shot Examples 注入上下文
   ↓
5. ReAct 执行循环（与训练相同）:
   ┌─────────────────────────────────────────┐
   │  for step in range(max_steps):          │
   │    Agent 生成 Action                     │
   │    观察环境反馈                          │
   │    动态判断是否需要检索新 Skill          │
   │    如果需要 → 检索并追加到上下文         │
   └─────────────────────────────────────────┘
   ↓
6. 返回结果
```

### 3.4 Skill 动态检索触发条件

在 ReAct 循环中，以下情况可触发 Skill 检索：

| 触发条件 | 说明 |
|---------|------|
| **动作失败** | Action 返回失败反馈，检索类似场景的 Skill |
| **重复动作** | 检测到重复动作模式，检索替代方案 |
| **长时间无进展** | 连续 N 步没有明显进展，检索相关提示 |
| **任务类型切换** | 子任务类型发生变化，如从"移动"切换到"操作" |
| **Agent 主动请求** | Agent 在 Thought 中明确请求 "use skill_xxx" |

## 4. 架构改动点

### 4.1 新增文件

| 文件路径 | 功能 |
|---------|------|
| `memrl/skills/skill.py` | Skill 数据类定义 |
| `memrl/skills/extractor.py` | Skill 提取器（使用 LLM 从轨迹提取） |
| `memrl/skills/store.py` | Skill 存储管理（JSON 文件读写） |
| `memrl/skills/retriever.py` | Skill 检索器（关键词/向量检索） |
| `memrl/skills/manager.py` | Skill 管理器（整合提取/存储/检索） |
| `memrl/skills/__init__.py` | 模块导出 |

### 4.2 修改文件

| 文件路径 | 修改内容 |
|---------|---------|
| `memrl/agent/memp_agent.py` | 新增 `skills` 参数到 `_construct_messages()`；在 `act()` 返回时附带是否需要检索新 Skill 的标识 |
| `memrl/run/base_runner.py` | Runner 接口新增 `skill_service` 相关方法 |
| `memrl/run/alfworld_rl_runner.py` | 集成 Skill 检索和提取逻辑（ReAct 循环中动态检索） |
| `memrl/run/bcb_runner.py` | 集成 Skill 检索和提取逻辑 |
| `configs/*.yaml` | 新增 `skill` 配置项 |

### 4.3 Agent 层改动

**MempAgent.act() 返回值调整**:
```python
# 现有实现
def act(self, observation: str, history_messages: List[Dict], first_step: bool = False) -> str:
    """返回: action 字符串"""

# 调整后
def act(self, observation: str, history_messages: List[Dict], first_step: bool = False) -> Tuple[str, bool]:
    """
    返回: (action, should_retrieve_skill)
    - action: 执行的 action 字符串
    - should_retrieve_skill: 是否需要检索新 Skill（由 LLM 判断或规则触发）
    """
```

**Skill 检索触发机制**:
1. **LLM 显式请求**: LLM 在 Thought 中输出 "Need relevant skill: [keywords]"
2. **规则触发**: 动作失败、重复动作、长步骤无进展等

### 4.3 SkillManager 接口设计

```python
class SkillManager:
    """Skill 层核心管理器"""

    def retrieve(
        self,
        task_description: str = None,
        task_type: str = None,
        k: int = 3,
        observation: str = None  # 新增：支持基于当前观察检索
    ) -> List[Skill]:
        """
        检索与当前上下文相关的 Skills

        三种检索模式:
        1. 基于任务描述检索 (task_description)
        2. 基于任务类型检索 (task_type)
        3. 基于当前观察检索 (observation) - 用于 ReAct 循环中动态检索
        """

    def retrieve_for_observation(
        self,
        observation: str,
        task_context: str = None,
        k: int = 2
    ) -> List[Skill]:
        """
        根据当前 Observation 动态检索相关 Skills
        用于 ReAct 循环中动作失败或需要提示时
        """

    def extract_and_save(
        self,
        trajectory: List[Dict],
        task_description: str,
        task_type: str,
        success: bool
    ) -> Optional[Skill]:
        """从成功轨迹中提取并保存 Skill"""

    def update_skill_after_use(
        self,
        skill_id: str,
        action: str,
        observation: str,
        success: bool
    ):
        """
        更新 Skill 使用记录
        记录本次使用的 action 和 observation，用于后续分析
        """

    def load_skill(self, skill_id: str) -> Optional[Skill]:
        """加载单个 Skill"""

    def get_all_skills(self) -> List[Skill]:
        """获取所有 Skills"""

    def get_applicable_skills(
        self,
        observation: str,
        task_type: str = None
    ) -> List[Skill]:
        """
        获取适用于当前 Observation 的 Skills
        用于 ReAct 循环中快速判断有哪些 Skill 可用
        """
```

### 4.4 Runner 集成点

```python
# === 初始化阶段 ===
skill_manager = SkillManager(config)

# === 任务开始前：初始检索 ===
skills = skill_manager.retrieve(
    task_description=task_description,
    task_type=task_type,
    k=3
)

# === ReAct 执行循环中：动态检索 ===
for step in range(max_steps):
    action, should_retrieve_skill = agent.act(
        observation=current_observation,
        history_messages=messages,
        first_step=(step == 0)
    )

    # 如果 Agent 判断需要新 Skill 或动作失败，动态检索
    if should_retrieve_skill or action_failed:
        new_skills = skill_manager.retrieve_for_observation(
            observation=current_observation,
            task_context=task_description,
            k=2
        )
        if new_skills:
            # 追加新 Skill 到上下文
            messages = append_skills_to_messages(messages, new_skills)

    # 执行动作...

# === 任务成功后：提取并保存 Skill ===
if success:
    skill_manager.extract_and_save(
        trajectory=trajectory,
        task_description=task_description,
        task_type=task_type,
        success=True
    )
```

```python
# 在 Runner 执行任务前
skills = skill_manager.retrieve(task_description, task_type, k=3)

# 在 Runner 构建 Prompt 时
messages = agent._construct_messages(
    task_description=task_description,
    retrieved_memories=retrieved_memories,
    task_type=task_type,
    skills=skills  # 新增参数
)

# 在任务成功后
if success:
    skill_manager.extract_and_save(trajectory, task_description, task_type, success)
```

## 5. 与 MemoryService 的关系

| 维度 | MemoryService | Skill 层 |
|------|---------------|----------|
| **存储内容** | 完整轨迹 + Q值 | 提炼的行动模式 |
| **粒度** | 细粒度（每任务一条） | 粗粒度（可跨任务复用） |
| **检索方式** | 向量相似度 | 关键词 + 任务类型 |
| **生命周期** | 随训练更新 Q 值 | 持久化，不轻易删除 |
| **使用方式** | 注入上下文 | 注入上下文（更精简） |

**关系**: Skill 层是 MemoryService 的补充，MemoryService 存储原始轨迹，Skill 层提炼通用模式。

## 6. 配置项（YAML）

```yaml
skill:
  enabled: true                    # 是否启用 Skill 功能
  extract_threshold: 0.7           # 提取 Skill 的最低成功率阈值
  retrieve_k: 3                    # 检索的 Top-K
  storage_dir: "skills"             # 存储目录
  similarity_threshold: 0.6       # 检索相似度阈值
  auto_extract: true               # 成功后自动提取
```

## 7. 后续扩展方向

1. **Skill 进化**: 当 Skill 成功率下降时，自动重新提取或合并
2. **Skill 评估**: 基于任务类型自动评估 Skill 的适用性
3. **Skill 版本管理**: 支持 Skill 的迭代更新
4. **跨任务 Skill 泛化**: 从多个成功轨迹中提炼通用 Skill
