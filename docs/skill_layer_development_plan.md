# Skill Layer 阶段性开发文档

本文档将 Skill 层的开发分解为 5 个增量阶段，每个阶段都可独立开发和测试。

---

## 阶段总览

| 阶段 | 名称 | 核心功能 | 交付物 | 依赖 |
|------|------|---------|--------|------|
| **Phase 1** | 基础数据模型 | Skill 数据结构和存储 | `skill.py`, `store.py` | 无 |
| **Phase 2** | Skill 存储 | JSON 文件读写和索引 | `skills/` 目录结构 | Phase 1 |
| **Phase 3** | Skill 提取 | LLM 从成功轨迹提取 Skill | `extractor.py` | Phase 1, 2 |
| **Phase 4** | Skill 检索 | 多种检索模式 | `retriever.py`, `manager.py` | Phase 2 |
| **Phase 5** | 失败分析 | 失败轨迹分析和 Skill 更新 | `analyzer.py`, 更新逻辑 | Phase 3 |
| **Phase 6** | Runner 集成 | 与现有 Runner 集成 | 集成代码 | Phase 4, 5 |

---

## Phase 1: 基础数据模型

### 目标
定义 Skill 的核心数据结构和基本操作。

### 交付物
- `memrl/skills/skill.py` - Skill 数据类和 dataclass 定义

### 详细设计

#### 1.1 定义 SkillStep 数据类
```python
@dataclass
class SkillStep:
    action: str                           # 动作
    observation_pattern: str             # 触发此动作的观察条件
    reasoning: str                       # 为什么要执行这个动作
```

#### 1.2 定义 Skill 数据类
```python
@dataclass
class Skill:
    skill_id: str                         # 唯一标识
    name: str                            # 技能名称
    description: str                     # 技能描述
    task_type: str                       # 任务类型
    trigger_keywords: List[str]          # 触发检索关键词
    applicable_observations: List[str]   # 适用观察条件
    steps: List[SkillStep]            # 执行步骤
    skill_type: str = "primitive"       # primitive | composite
    parent_skill_id: Optional[str] = None

    # 统计信息
    success_rate: float = 1.0
    usage_count: int = 0
    last_used_at: Optional[str] = None
    created_at: str = ""
    source_trajectory_id: Optional[str] = None

    # 失败相关
    failure_scenarios: List[Dict] = field(default_factory=list)
    antipatterns: List[Dict] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    deprecated: bool = False

    # 方法
    def to_dict(self) -> Dict
    @classmethod
    def from_dict(cls, data: Dict) -> Skill
    def add_failure_scenario(self, scenario: Dict)
    def add_antipattern(self, pattern: Dict)
    def add_constraint(self, constraint: str)
    def update_stats(self, success: bool)
```

#### 1.3 定义 SkillUpdate 数据类
```python
@dataclass
class SkillUpdate:
    skill_id: str
    update_type: str  # "add_constraint" | "add_failure_scenario" | "create_antipattern" | "deprecate" | "merge"
    new_constraints: List[str] = field(default_factory=list)
    warning: str = ""
    failure_scenario: Optional[Dict] = None
    antipattern: Optional[Dict] = None
    deprecated: bool = False
```

### 测试
```python
def test_skill_creation():
    skill = Skill(
        skill_id="skill_test_001",
        name="测试技能",
        description="这是一个测试技能",
        task_type="test",
        trigger_keywords=["test"],
        applicable_observations=["test obs"],
        steps=[SkillStep(action="go", observation_pattern="test", reasoning="test")]
    )
    assert skill.skill_id == "skill_test_001"
    assert skill.success_rate == 1.0

def test_skill_to_dict():
    skill = Skill(...)
    data = skill.to_dict()
    assert isinstance(data, dict)
    restored = Skill.from_dict(data)
    assert restored.skill_id == skill.skill_id
```

### 验收标准
- [ ] `Skill` 和 `SkillStep` dataclass 定义正确
- [ ] `to_dict()` / `from_dict()` 序列化/反序列化正常
- [ ] `update_stats()` 能正确更新 success_rate 和 usage_count
- [ ] 单元测试通过

---

## Phase 2: Skill 存储

### 目标
实现 Skill 的持久化存储，支持 JSON 文件读写和索引管理。

### 交付物
- `memrl/skills/store.py` - SkillStore 存储管理类
- `skills/` 目录结构
- `__init__.py` 导出

### 详细设计

#### 2.1 目录结构
```
skills/
├── index.json              # Skill 索引
├── skill_001.json         # 单个 Skill 文件
├── skill_002.json
└── ...
```

#### 2.2 SkillStore 实现
```python
class SkillStore:
    """Skill 存储管理"""

    def __init__(self, storage_dir: str = "skills"):
        self.storage_dir = Path(storage_dir)
        self.index_path = self.storage_dir / "index.json"
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    # === 基础 CRUD ===

    def save(self, skill: Skill) -> str:
        """保存 Skill 到文件"""
        skill_path = self.storage_dir / f"{skill.skill_id}.json"
        with open(skill_path, "w", encoding="utf-8") as f:
            json.dump(skill.to_dict(), f, ensure_ascii=False, indent=2)
        self._update_index(skill)
        return skill.skill_id

    def load(self, skill_id: str) -> Optional[Skill]:
        """从文件加载 Skill"""
        skill_path = self.storage_dir / f"{skill_id}.json"
        if not skill_path.exists():
            return None
        with open(skill_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Skill.from_dict(data)

    def delete(self, skill_id: str) -> bool:
        """删除 Skill"""
        skill_path = self.storage_dir / f"{skill_id}.json"
        if skill_path.exists():
            skill_path.unlink()
            self._remove_from_index(skill_id)
            return True
        return False

    # === 批量操作 ===

    def get_all_skills(self) -> List[Skill]:
        """加载所有 Skills"""
        index = self._load_index()
        return [
            self.load(entry["skill_id"])
            for entry in index.get("skills", [])
        ]

    def get_skills_by_type(self, task_type: str) -> List[Skill]:
        """按任务类型获取 Skills"""
        index = self._load_index()
        skill_ids = [
            entry["skill_id"]
            for entry in index.get("skills", [])
            if entry["task_type"] == task_type or entry["task_type"].startswith(task_type)
        ]
        return [self.load(sid) for sid in skill_ids if self.load(sid)]

    # === 索引管理 ===

    def _load_index(self) -> Dict:
        """加载索引文件"""
        if not self.index_path.exists():
            return {"skills": [], "total_count": 0}
        with open(self.index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _update_index(self, skill: Skill):
        """更新索引"""
        index = self._load_index()

        # 查找是否已存在
        for entry in index["skills"]:
            if entry["skill_id"] == skill.skill_id:
                entry.update({
                    "name": skill.name,
                    "task_type": skill.task_type,
                    "keywords": skill.trigger_keywords,
                })
                break
        else:
            # 新增
            index["skills"].append({
                "skill_id": skill.skill_id,
                "name": skill.name,
                "task_type": skill.task_type,
                "keywords": skill.trigger_keywords,
            })

        index["total_count"] = len(index["skills"])

        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    # === Skill 更新 ===

    def update_skill(self, skill_id: str, updates: List[SkillUpdate]) -> bool:
        """根据 SkillUpdate 更新 Skill"""
        skill = self.load(skill_id)
        if not skill:
            return False

        for update in updates:
            if update.update_type == "add_constraint":
                skill.constraints.extend(update.new_constraints)
            elif update.update_type == "add_failure_scenario":
                skill.failure_scenarios.append(update.failure_scenario)
            elif update.update_type == "create_antipattern":
                skill.antipatterns.append(update.antipattern)
            elif update.update_type == "deprecate":
                skill.deprecated = True

        self.save(skill)
        return True
```

### 测试
```python
def test_store_save_and_load(tmp_path):
    store = SkillStore(storage_dir=str(tmp_path))
    skill = Skill(...)
    store.save(skill)

    loaded = store.load(skill.skill_id)
    assert loaded.skill_id == skill.skill_id
    assert loaded.name == skill.name

def test_store_index(tmp_path):
    store = SkillStore(storage_dir=str(tmp_path))
    store.save(Skill(skill_id="s1", ...))
    store.save(Skill(skill_id="s2", ...))

    index = store._load_index()
    assert index["total_count"] == 2

def test_store_get_by_type(tmp_path):
    store = SkillStore(storage_dir=str(tmp_path))
    store.save(Skill(skill_id="s1", task_type="alfworld/pick", ...))
    store.save(Skill(skill_id="s2", task_type="alfworld/place", ...))

    results = store.get_skills_by_type("alfworld/pick")
    assert len(results) == 1
    assert results[0].skill_id == "s1"
```

### 验收标准
- [ ] Skill 保存到 JSON 文件正常
- [ ] 从 JSON 文件加载正常
- [ ] 索引文件 index.json 维护正确
- [ ] `get_all_skills()` 返回所有 Skills
- [ ] `get_skills_by_type()` 按类型筛选正常
- [ ] `update_skill()` 根据 SkillUpdate 修改 Skill 正常
- [ ] 单元测试通过

### Phase 1 → Phase 2 依赖
```
Phase 1: Skill 数据类 (skill.py)
              ↓
Phase 2: SkillStore (store.py) 使用 Skill 类
```

---

## Phase 3: Skill 提取

### 目标
实现 Skill Extractor，从成功轨迹中提取 Skill。

### 交付物
- `memrl/skills/extractor.py` - SkillExtractor 提取器

### 详细设计

#### 3.1 SkillExtractor 核心实现

```python
class SkillExtractor:
    """从轨迹中提取 Skill 的提取器"""

    def __init__(
        self,
        llm: BaseLLM,
        min_steps: int = 2,
        max_steps: int = 10,
    ):
        self.llm = llm
        self.min_steps = min_steps
        self.max_steps = max_steps

    def extract(
        self,
        trajectory: List[Dict],      # 消息格式轨迹
        task_description: str,
        task_type: str,
        source_trajectory_id: str = None,
    ) -> Optional[Skill]:
        """
        从成功轨迹中提取 Skill
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

        if not extracted:
            return None

        # Step 3: 构建 Skill
        return self._build_skill(
            extracted=extracted,
            task_description=task_description,
            task_type=task_type,
            source_trajectory_id=source_trajectory_id,
        )

    def _parse_trajectory(self, trajectory: List[Dict]) -> List[Dict[str, str]]:
        """解析轨迹，提取 action-observation 对"""
        # 见设计文档 2.1.3

    def _llm_refine(self, action_obs_pairs, task_description, task_type) -> Optional[Dict]:
        """使用 LLM 提炼"""
        # 见设计文档 2.1.3，使用 Prompt 提取

    def _build_skill(self, extracted, task_description, task_type, source_trajectory_id) -> Skill:
        """构建 Skill 对象"""
        import hashlib, time
        skill_id = f"skill_{int(time.time())}_{hashlib.md5(task_description.encode()).hexdigest()[:8]}"

        steps = [
            SkillStep(
                action=s.get("action", ""),
                observation_pattern=s.get("observation_pattern", ""),
                reasoning=s.get("reasoning", ""),
            )
            for s in extracted.get("steps", [])
        ]

        return Skill(
            skill_id=skill_id,
            name=extracted.get("name", task_description[:50]),
            description=extracted.get("description", task_description),
            task_type=task_type,
            trigger_keywords=extracted.get("trigger_keywords", []),
            applicable_observations=extracted.get("applicable_observations", []),
            steps=steps,
            skill_type=extracted.get("skill_type", "primitive"),
            success_rate=1.0,
            usage_count=0,
            created_at=datetime.now().isoformat(),
            source_trajectory_id=source_trajectory_id,
        )
```

#### 3.2 提取触发条件

```python
class ExtractionTrigger:
    """判断是否应该提取 Skill"""

    def __init__(self, config: SkillConfig):
        self.config = config
        self.extractor = SkillExtractor(llm=config.llm)

    def should_extract(
        self,
        task_type: str,
        trajectory: List[Dict],
        success: bool,
        current_success_rate: float = 0.0,
    ) -> Tuple[bool, str]:
        """
        判断是否应该提取
        Returns: (should_act, action_type)
        action_type: "extract_new" | "none"
        """

        if not success:
            return False, "none"  # Phase 5 处理失败

        if not self.config.auto_extract:
            return False, "none"

        if self._has_enough_steps(trajectory):
            return True, "extract_new"

        return False, "none"

    def _has_enough_steps(self, trajectory: List[Dict]) -> bool:
        action_count = sum(
            1 for msg in trajectory
            if msg.get("role") == "assistant" and "Action:" in msg.get("content", "")
        )
        return action_count >= self.extractor.min_steps
```

### 测试
```python
def test_parse_trajectory():
    extractor = SkillExtractor(llm=mock_llm)
    trajectory = [
        {"role": "assistant", "content": "Thought: test\nAction: go to fridge"},
        {"role": "user", "content": "Observation: You are in kitchen"},
    ]
    pairs = extractor._parse_trajectory(trajectory)
    assert len(pairs) == 1
    assert pairs[0]["action"] == "go to fridge"
```

### 验收标准
- [ ] 轨迹解析正确提取 action-observation 对
- [ ] LLM 提炼生成有效的 Skill JSON
- [ ] `extract()` 返回有效的 Skill 对象
- [ ] 成功轨迹触发提取
- [ ] 单元测试通过

### Phase 2 → Phase 3 依赖
```
Phase 2: SkillStore (store.py)
              ↓
Phase 3: SkillExtractor (extractor.py)
         - 使用 SkillStore 保存提取的 Skill
         - 使用 Skill 类
```

---

## Phase 4: Skill 检索

### 目标
实现多种检索模式，包括纯 LLM 推理检索。

### 交付物
- `memrl/skills/retriever.py` - 多种检索模式
- `memrl/skills/manager.py` - SkillManager 整合

### 详细设计

#### 4.1 SkillRetriever 检索器

```python
class SkillRetriever:
    """Skill 检索器，支持多种检索模式"""

    def __init__(
        self,
        skill_store: SkillStore,
        llm: BaseLLM = None,           # 用于 LLM 检索
        embedder: BaseEmbedder = None,   # 用于向量检索
    ):
        self.skill_store = skill_store
        self.llm = llm
        self.embedder = embedder

    def retrieve(
        self,
        query: str = None,
        task_type: str = None,
        observation: str = None,
        k: int = 3,
        method: str = "llm",  # "llm" | "keyword" | "vector" | "hybrid"
    ) -> List[Skill]:
        """
        检索相关 Skills
        """

        if method == "llm":
            return self._retrieve_with_llm(query, observation, k)
        elif method == "keyword":
            return self._retrieve_with_keyword(query, task_type, k)
        elif method == "vector":
            return self._retrieve_with_vector(query, k)
        elif method == "hybrid":
            return self._retrieve_hybrid(query, task_type, observation, k)
        else:
            return []

    def _retrieve_with_llm(
        self,
        query: str,
        observation: str,
        k: int,
    ) -> List[Skill]:
        """
        纯 LLM 推理检索 (Phase 4 核心)
        """
        all_skills = self.skill_store.get_all_skills()
        if not all_skills:
            return []

        # 格式化 Skills 列表
        skills_list = self._format_skills_for_llm(all_skills)

        prompt = f"""你是一个任务执行助手，擅长根据任务描述匹配并使用相关技能(Skill)。

## 可用技能列表
{skills_list}

## 任务
当前任务描述: {query}
当前观察: {observation or '无'}

## 你的任务
仔细阅读所有可用技能，判断哪些技能与当前任务相关。
输出格式:
```
相关技能: skill_id_1, skill_id_2, ...
```
如果没有相关技能:
```
相关技能: None
```
"""

        response = self.llm.generate([{"role": "user", "content": prompt}])
        matched_ids = self._parse_llm_response(response)

        # 返回匹配的 Skills (最多 k 个)
        matched_skills = [s for s in all_skills if s.skill_id in matched_ids]
        return matched_skills[:k]

    def _format_skills_for_llm(self, skills: List[Skill]) -> str:
        """格式化 Skills 列表供 LLM 读取"""
        lines = []
        for s in skills:
            lines.append(f"""- skill_id: {s.skill_id}
  name: {s.name}
  description: {s.description}
  task_type: {s.task_type}
  trigger_keywords: {s.trigger_keywords}
  applicable_observations: {s.applicable_observations}""")
        return "\n".join(lines)

    def _parse_llm_response(self, response: str) -> List[str]:
        """从 LLM 响应解析 skill_ids"""
        import re
        match = re.search(r'相关技能:\s*(.+)', response)
        if match:
            ids_str = match.group(1).strip()
            if ids_str == "None":
                return []
            return [id.strip() for id in ids_str.split(",")]
        return []

    def _retrieve_with_keyword(self, query, task_type, k) -> List[Skill]:
        """关键词检索"""
        # 实现见设计文档 2.3.4

    def _retrieve_with_vector(self, query, k) -> List[Skill]:
        """向量检索"""
        # 实现见设计文档 2.3.4

    def _retrieve_hybrid(self, query, task_type, observation, k) -> List[Skill]:
        """混合检索"""
        # 先 keyword 快速筛选，再用 LLM 精排
```

#### 4.2 SkillManager 整合

```python
class SkillManager:
    """Skill 层核心管理器，整合所有功能"""

    def __init__(
        self,
        config: SkillConfig,
        llm: BaseLLM,
        embedder: BaseEmbedder = None,
    ):
        self.config = config
        self.store = SkillStore(storage_dir=config.storage_dir)
        self.extractor = SkillExtractor(llm=llm)
        self.retriever = SkillRetriever(
            skill_store=self.store,
            llm=llm,
            embedder=embedder,
        )

    # === 检索 ===
    def retrieve(
        self,
        task_description: str = None,
        task_type: str = None,
        observation: str = None,
        k: int = 3,
    ) -> List[Skill]:
        """检索相关 Skills"""
        return self.retriever.retrieve(
            query=task_description,
            task_type=task_type,
            observation=observation,
            k=k,
            method=self.config.retrieval_method,
        )

    # === 提取 ===
    def extract_and_save(
        self,
        trajectory: List[Dict],
        task_description: str,
        task_type: str,
        success: bool = True,
    ) -> Optional[Skill]:
        """提取并保存 Skill"""
        if not success:
            return None

        skill = self.extractor.extract(
            trajectory=trajectory,
            task_description=task_description,
            task_type=task_type,
        )

        if skill:
            self.store.save(skill)

        return skill

    # === 更新统计 ===
    def update_skill_stats(self, skill_id: str, success: bool):
        """更新 Skill 使用统计"""
        skill = self.store.load(skill_id)
        if skill:
            skill.update_stats(success)
            self.store.save(skill)

    # === 加载/查询 ===
    def load_skill(self, skill_id: str) -> Optional[Skill]:
        return self.store.load(skill_id)

    def get_all_skills(self) -> List[Skill]:
        return self.store.get_all_skills()
```

### 测试
```python
def test_retrieve_with_llm(mock_llm, tmp_path):
    store = SkillStore(storage_dir=str(tmp_path))
    store.save(Skill(skill_id="s1", name="开冰箱", task_type="alfworld", trigger_keywords=["冰箱"], ...))
    store.save(Skill(skill_id="s2", name="开微波炉", task_type="alfworld", trigger_keywords=["微波炉"], ...))

    retriever = SkillRetriever(store, llm=mock_llm)
    results = retriever.retrieve(query="我需要打开冰箱取东西", method="llm")
    assert len(results) >= 1
```

### 验收标准
- [ ] LLM 检索能正确匹配 Skills
- [ ] 关键词检索工作正常
- [ ] 混合检索能结合多种模式
- [ ] SkillManager 整合检索和提取
- [ ] 单元测试通过

### Phase 3 → Phase 4 依赖
```
Phase 3: SkillExtractor (extractor.py)
              ↓
Phase 4: SkillRetriever (retriever.py) + SkillManager (manager.py)
         - 检索器需要加载 Skills (依赖 SkillStore)
         - Manager 整合提取和检索
```

---

## Phase 5: 失败分析

### 目标
实现失败轨迹分析，生成 Skill 更新。

### 交付物
- `memrl/skills/analyzer.py` - FailureAnalyzer 失败分析器
- 更新 SkillManager 中的 `analyze_and_update()` 方法

### 详细设计

#### 5.1 FailureAnalyzer

```python
class FailureAnalyzer:
    """分析失败轨迹，生成教训或更新现有技能"""

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def analyze(
        self,
        failed_trajectory: List[Dict],
        task_description: str,
        task_type: str,
    ) -> Optional[Dict]:
        """
        分析失败轨迹，返回失败分析结果
        """

        pairs = self._parse_trajectory(failed_trajectory)
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

## 输出格式 (JSON)
{{
  "failure_step": 失败步骤索引,
  "failure_action": "失败的动作",
  "failure_reason": "wrong_action | wrong_order | missing_prerequisite | environment_error",
  "failure_detail": "详细描述",
  "lesson": "教训总结（以后应该怎么做）",
  "avoid_keywords": ["应该避免的关键词1", "关键词2"],
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

    def generate_updates(
        self,
        failure_analysis: Dict,
        existing_skills: List[Skill],
    ) -> List[SkillUpdate]:
        """
        根据失败分析生成对现有 Skills 的更新
        """

        updates = []
        for skill in existing_skills:
            if self._is_related_skill(skill, failure_analysis):
                update = self._create_update(skill, failure_analysis)
                if update:
                    updates.append(update)

        return updates

    def _is_related_skill(self, skill: Skill, analysis: Dict) -> bool:
        """判断 Skill 是否与失败分析相关"""
        # 检查 task_type、keywords 等
        return True  # 简化实现

    def _create_update(self, skill: Skill, analysis: Dict) -> Optional[SkillUpdate]:
        """创建 SkillUpdate"""
        reason = analysis.get("failure_reason", "")

        if reason == "missing_prerequisite":
            return SkillUpdate(
                skill_id=skill.skill_id,
                update_type="add_constraint",
                new_constraints=[analysis.get("failure_detail", "")],
            )
        elif reason == "wrong_action":
            return SkillUpdate(
                skill_id=skill.skill_id,
                update_type="create_antipattern",
                antipattern={
                    "action": analysis.get("failure_action"),
                    "wrong_reason": analysis.get("failure_detail"),
                    "correct_approach": analysis.get("correct_approach"),
                },
            )
        # ...
```

#### 5.2 更新 SkillManager

```python
class SkillManager:
    # ... Phase 4 的内容 ...

    def analyze_failure_and_update(
        self,
        failed_trajectory: List[Dict],
        task_description: str,
        task_type: str,
    ) -> List[SkillUpdate]:
        """
        分析失败轨迹并更新相关 Skills
        """

        # Step 1: LLM 分析失败原因
        analysis = self.failure_analyzer.analyze(
            failed_trajectory=failed_trajectory,
            task_description=task_description,
            task_type=task_type,
        )

        if not analysis:
            return []

        # Step 2: 获取相关 Skills
        related_skills = self.store.get_skills_by_type(task_type)

        # Step 3: 生成更新
        updates = self.failure_analyzer.generate_updates(analysis, related_skills)

        # Step 4: 应用更新
        for update in updates:
            self.store.update_skill(update.skill_id, [update])

        return updates
```

### 验收标准
- [ ] 失败轨迹解析正确
- [ ] LLM 生成有效的失败分析
- [ ] 生成正确的 SkillUpdate
- [ ] 更新应用到现有 Skills
- [ ] 单元测试通过

### Phase 3 → Phase 5 依赖
```
Phase 3: SkillExtractor (extractor.py) - 复用轨迹解析
              ↓
Phase 5: FailureAnalyzer (analyzer.py)
         - 使用 Skill 数据类
         - 使用 SkillStore 更新
```

---

## Phase 6: Runner 集成

### 目标
将 Skill 层与现有 Runner 集成，实现完整的训练/推理流程。

### 交付物
- 修改 `memrl/run/alfworld_rl_runner.py`
- 修改 `memrl/run/bcb_runner.py`
- 新增配置项

### 详细设计

#### 6.1 配置项

```yaml
skill:
  enabled: true                    # 是否启用 Skill 功能
  storage_dir: "skills"            # 存储目录
  retrieval_method: "llm"         # 检索模式: llm | keyword | vector | hybrid
  extract_threshold: 0.7           # 提取成功率阈值
  retrieve_k: 3                   # 检索 Top-K
  auto_extract: true              # 成功后自动提取
  auto_analyze_failure: true      # 失败后自动分析
```

#### 6.2 Runner 集成

```python
# memrl/run/alfworld_rl_runner.py

class AlfworldRunner:
    def __init__(self, ..., skill_config: SkillConfig = None):
        # ... 现有代码 ...

        # 新增: Skill 层初始化
        if skill_config and skill_config.enabled:
            self.skill_manager = SkillManager(
                config=skill_config,
                llm=llm_provider,
                embedder=embedding_provider,
            )
        else:
            self.skill_manager = None

    def _sample_from_batch(self, ...):
        # ... 现有代码 ...

        # === 任务开始前: 检索 Skills ===
        if self.skill_manager:
            skills = self.skill_manager.retrieve(
                task_description=task_desc,
                task_type=task_type,
                observation=None,
                k=self.skill_config.retrieve_k,
            )
        else:
            skills = []

        # === 构建消息时注入 Skills ===
        messages = self.agent._construct_messages(
            task_description=task_desc,
            retrieved_memories=retrieved_memories,
            task_type=task_type,
            skills=skills,  # 新增参数
        )

        # === ReAct 循环 ===
        for step in range(self.max_steps):
            action = self.agent.act(observation, messages, first_step=(step==0))
            # ... 执行 ...

            # === 动态 Skill 检索 (可选) ===
            if self.skill_manager and should_retrieve_skill:
                new_skills = self.skill_manager.retrieve(
                    task_description=None,
                    task_type=task_type,
                    observation=observation,
                    k=2,
                )
                if new_skills:
                    messages = self._append_skills_to_messages(messages, new_skills)

        # === 任务完成后: 提取或分析 ===
        if self.skill_manager:
            if success:
                self.skill_manager.extract_and_save(
                    trajectory=trajectory,
                    task_description=task_desc,
                    task_type=task_type,
                    success=True,
                )
            else:
                self.skill_manager.analyze_failure_and_update(
                    failed_trajectory=trajectory,
                    task_description=task_desc,
                    task_type=task_type,
                )

    def _append_skills_to_messages(self, messages, skills):
        """将 Skills 追加到消息中"""
        if not skills:
            return messages

        skills_text = "\n\n".join([
            f"### Skill: {s.name}\n{s.description}\nSteps: " +
            ", ".join([st.action for st in s.steps])
            for s in skills
        ])

        skill_context = {
            "role": "system",
            "content": f"你可以使用以下相关技能:\n{skills_text}"
        }

        # 在最后一个 user 消息后插入
        return messages + [skill_context]
```

#### 6.3 Agent 层修改

```python
# memrl/agent/memp_agent.py

def _construct_messages(
    self,
    task_description: str,
    retrieved_memories: Dict,
    task_type: str,
    skills: List[Skill] = None,  # 新增参数
) -> List[Dict[str, str]]:

    # ... 现有代码 ...

    # 新增: 添加 Skills 到上下文
    if skills:
        skills_context = self._format_skills(skills)
        messages.append({"role": "system", "content": skills_context})

    return messages

def _format_skills(self, skills: List[Skill]) -> str:
    """格式化 Skills 供 Agent 参考"""
    lines = ["你可以使用以下相关技能:\n"]
    for s in skills:
        lines.append(f"## {s.name}")
        lines.append(f"描述: {s.description}")
        lines.append(f"适用观察: {s.applicable_observations}")
        lines.append(f"执行步骤: " + " → ".join([st.action for st in s.steps]))
        if s.constraints:
            lines.append(f"注意: {'; '.join(s.constraints)}")
        if s.antipatterns:
            lines.append(f"禁忌: {'; '.join([a['action'] for a in s.antipatterns])}")
        lines.append("")
    return "\n".join(lines)
```

### 验收标准
- [ ] 配置文件正确解析 skill 配置项
- [ ] 任务开始前正确检索 Skills
- [ ] Skills 正确注入 Agent 上下文
- [ ] 成功任务触发 Skill 提取
- [ ] 失败任务触发失败分析
- [ ] 集成测试通过

### Phase 4, 5 → Phase 6 依赖
```
Phase 4: SkillRetriever + SkillManager
Phase 5: FailureAnalyzer
              ↓
Phase 6: Runner 集成
         - 使用 SkillManager 进行检索和提取
         - 使用 FailureAnalyzer 分析失败
```

---

## 开发顺序建议

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
   ↓         ↓         ↓         ↓         ↓         ↓
 基础模型   存储      提取      检索     失败分析    集成
```

**每个 Phase 完成后都应该：**
1. 编写单元测试
2. 确保测试通过
3. 可以独立运行简单 demo
4. 提交到 git

**Phase 6 完成后：**
1. 完整的端到端测试
2. 性能基准测试
3. 文档更新

---

## 附录: 文件清单

| Phase | 文件 | 行数估计 |
|-------|------|---------|
| 1 | `memrl/skills/skill.py` | ~100 |
| 2 | `memrl/skills/store.py` | ~200 |
| 3 | `memrl/skills/extractor.py` | ~250 |
| 4 | `memrl/skills/retriever.py` | ~300 |
| 4 | `memrl/skills/manager.py` | ~150 |
| 5 | `memrl/skills/analyzer.py` | ~200 |
| 6 | Runner 集成修改 | ~150/Runner |

**总计约 1350 行新代码**
