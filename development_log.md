# qskill 开发日志

## 2026-05-07 - 论文评审意见整理

### 评审文档

创建 `docs/paper_review.md`，整理了关于当前 qskill 论文工作的评审意见。

### 论文 Roadmap

创建 `docs/paper_roadmap.md`，包含：

**核心贡献 Statement（推荐版本）**：
> qskill: A non-parametric skill evolution approach that decouples stable skill retention from plastic skill acquisition. By combining Q-value guided retrieval, environment-driven skill value updates, and automatic skill culling/merging, qskill enables agents to continuously evolve their skill libraries without weight updates.

**Culling/Merging 实现逻辑**：
- Culling: `skill_value < threshold` + `usage_count >= min` 时淘汰
- Merging: `cosine_similarity >= 0.85` 的技能标记为可合并（合并执行未实现）

**下一步计划**：
1. 补足 4 benchmark 实验
2. 消融实验（Q-value 有/无、Culling 有/无）
3. 实现 Merging 合并执行
4. 理论分析（Q-value 收敛性）

### 核心评价

- 当前工作处于"系统实现"阶段，距离论文发表需要显著科研贡献提炼
- 优点：工程扎实、memory+skill 协同、多类别技能设计
- 不足：贡献点不清晰、与前沿工作差异不足、实验验证不充分

### 建议突破方向

1. **Skill Evolution Theory** - 技能如何"正确"演化的理论
2. **Two-Phase Retrieval 理论分析** - 形式化证明两阶段优于单阶段
3. **与 Skill0 结合** - 训练时内化 + 运行时检索 正交结合
4. **Skill Value 理论性质** - Q-value 收敛性证明

### 下一步

- 补足实验：4 benchmark + 消融 + 统计显著性
- 提炼核心贡献 statement
- 参考 Skill0/SkillMOO 写作方式

---

## 2026-05-07 - BCB Skill Layer 集成

### 修改的文件

1. **qskill/run/bcb_runner.py**
   - `__init__`: 添加 `skill_integrator` 参数
   - `_generate_raw()`: 添加 `skill_context` 参数
   - `_generate_code()`: 添加 `skill_context` 参数
   - `_get_task_type()`: 新增辅助方法，从 task 提取任务类型（基于 entry_point 和 libs）
   - `_run_phase()`: 添加技能检索、价值更新、技能提取逻辑

2. **run/run_bcb.py**
   - 导入 `create_skill_integrator`
   - 添加 `--disable_skills` 命令行参数
   - 初始化 `skill_integrator` 并传递给 BCBRunner

3. **run/run_alfworld.py**
   - 修复 bug：移除不存在的 `initialize()` 调用

### BCB 任务类型定义

BCB 的任务类型使用 `entry_point` 和 `libs` 字段构造：
```python
# 例如: libs=["pandas"], entry_point="filter_data"
# task_type = "pandas/filter_data"
```

### 运行方式

```bash
# 带 skill layer 运行
python run/run_bcb.py --config configs/rl_bcb_config.yaml --epochs 3

# 不带 skill layer 运行（对比实验）
python run/run_bcb.py --config configs/rl_bcb_config.yaml --epochs 3 --disable_skills
```

---

## 2026-04-29 - 项目整理：重命名 + 导入修复

### 背景

项目从 `memrl` 重命名为 `qskill` 后，存在多处残留引用，且 `manager.py` 和测试文件导入了不存在的模块。

### 修改的文件

#### 1. 重命名残留修复

| 文件 | 修改内容 |
|------|----------|
| `CLAUDE.md` | 更新 `memrl/` → `qskill/` 路径引用 |
| `pyproject.toml` | 项目名 `memrl` → `qskill`，脚本入口、pytest 配置更新 |
| `README.md` | 命名空间、布局说明、引用更新 |
| `qskill/__init__.py` | 文档字符串更新 |
| `qskill/skills/__init__.py` | 文档字符串更新 |
| `qskill/__version__.py` | 文档字符串和团队名更新 |
| `qskill/run/__init__.py` | 注释中的路径更新 |
| `qskill/cli/main.py` | CLI 文档和 prog_name 更新 |

#### 2. 关键 Bug 修复

| 文件 | 修改内容 |
|------|----------|
| `qskill/skills/manager.py` | 修复错误的 `memrl.skills.*` 导入 → `qskill.skills.*` |
| `qskill/run/alfworld_rl_runner.py` | 修复注释中的路径 `memrl/` → `qskill/` |

#### 3. 缺失模块创建

`manager.py` 和测试期望的模块 (`SkillStore`, `SkillRetriever`, `SkillExtractor`, `ExtractionTrigger`) 从未实现。创建了简化版本来提供向后兼容：

| 文件 | 说明 |
|------|------|
| `qskill/skills/extractor.py` | `SkillConfig`, `SkillExtractor`, `ExtractionTrigger` 类 |
| `qskill/skills/store.py` | `SkillStore` 类 - JSON 文件存储管理 |
| `qskill/skills/retriever.py` | `SkillRetriever` 类 - 基于 skill_value 的检索 |

#### 4. 测试文件导入修复

以下测试文件的 `memrl.skills.*` 导入已改为 `qskill.skills.*`：

- `tests/test_extractor.py`
- `tests/test_manager.py`
- `tests/test_integration.py`
- `tests/test_store.py`
- `tests/test_retriever.py`

#### 5. 其他

- `.gitignore`: 添加 `.coverage`
- `configs/rl_bcb_config.yaml`: 更新注释中的路径引用

### 注意事项

- `development_log.md` 和 `docs/*.md` 中的 `memrl` 引用是历史记录，无需修改
- `configs/*.yaml` 中的 `user_id` 和 `experiment_name` 标识符保持原样
- 新创建的模块 (`store.py`, `retriever.py`, `extractor.py`) 是简化实现
- 实际的技能层实现在 `BatchSkillIntegrator` 和 `BatchSkillExtractor` 中

---

## 2026-04-01 - 技能检索修复 + 提示词改进

### 问题诊断

1. **任务类型检测失效**: `task_type` 是 `game.tw-pddl`（无效格式），导致无法识别 pick_and_place/cool/heat/clean 类型
2. **检索结果高度同质化**: 所有任务检索到的都是相同的4个通用技能
3. **技能内容不够具体**: 缺少失败恢复指导，导致重复失败动作

### 修改的文件

#### 1. `qskill/skills/batch_integration.py`
- **修复 `_detect_task_type()`**: 改进关键词匹配逻辑，支持 "put X in Y" 模式检测 pick_and_place
- **修复 `_normalize_task_type()`**: 添加 fallback，当 task_type 无法归一化时，从 task_description 检测类型
- **添加 fallback 逻辑**: 在 `_retrieve_embedding()` 中，当 normalized_type 无效时，使用 `_detect_task_type()` 检测

#### 2. `qskill/skills/prompts.py`
- **增强 `GENERAL_SKILL_EXTRACTION_PROMPT`**:
  - 添加 **Failure Recovery** 字段要求
  - 强制提取三个关键技能：重复动作失败、表面优先搜索、物体位置精确性
- **增强 `TASK_SPECIFIC_SKILL_EXTRACTION_PROMPT`**:
  - 添加 `task_type_specific_rules` 参数
  - 新增 `TASK_TYPE_SPECIFIC_RULES` 字典，包含每种任务类型的critical rules
- **增强 `COMMON_MISTAKES_EXTRACTION_PROMPT`**:
  - 添加五种高影响力失败模式识别指导
- **增强 `TASK_SUMMARIZATION_PROMPT`**:
  - 添加潜在陷阱识别（"put a hot X"、数量"two"、位置区分等）
  - 输出格式添加 "Potential Issues" 行

### 测试结果对比

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 成功率 | 70% | 50% (不同任务样本) |
| 检索技能差异化 | 无 | 有（检索到特定技能） |
| Token消耗 | 3.83M | 3.12M |

### 改进效果

修复后不同任务类型检索到的技能：
- pick_and_place: `execute-pick-and-place`, `pick-and-place-execution`
- cool: `navigate-to-cooling-appliance`, `cool-item-with-fridge`
- heat: `heat-appliance-setup`, `prioritize-target-search`
- clean: `execute-clean-task-with-location-check`

---

## 2026-03-27 - 技能价值（Skill Value）机制

### 背景
为技能库新增技能价值（Q值）属性，用于衡量技能的实用性。结合语义相似度，实现更智能的技能检索。

### 修改的文件

#### 1. `memrl/skills/skill.py`
- **新增字段**: `skill_value: float = 0.0` - 技能价值初始为0
- **新增方法**: `update_skill_value(success: bool, alpha: float = 0.5)`
  - 使用 Q-learning 公式: `Q_new ← Q_old + α(r - Q_old)`
  - 成功时 r=1，失败时 r=0
- **更新方法**: `to_dict()` 和 `from_dict()` - 包含 skill_value 字段

#### 2. `memrl/configs/config.py`
- **SkillConfig 新增字段**:
  - `value_alpha: float = 0.5` - Q值更新学习率
  - `value_lambda: float = 0.5` - 检索时Q值权重
  - `retrieve_general: int = 1` - 检索的通用技能数量
  - `retrieve_task_specific: int = 1` - 检索的任务特定技能数量
  - `retrieve_common_mistakes: int = 1` - 检索的常见错误数量

#### 3. `memrl/skills/batch_integration.py`
- **__init__ 新增参数**: `value_alpha`, `value_lambda`, `retrieve_general`, `retrieve_task_specific`, `retrieve_common_mistakes`
- **重写 `_retrieve_embedding()`**: 使用新的分类检索逻辑
  - 三种类型独立计算混合评分 `(1-λ)×sim + λ×Q`
  - 每种类型按配置的数量的检索，再按混合评分排序
- **新增方法**: `update_skill_value_by_name()` - 根据技能名称更新Q值并持久化
- **新增方法**: `_save_updated_index()` - 保存更新后的技能索引
- **新增方法**: `extract_and_save_skill()` - `add_trajectory` 的别名，保持接口兼容

#### 4. `memrl/skills/integration.py`
- **create_skill_integrator()**: 传递所有新参数
- **新增**: `SkillIntegrator = BatchSkillIntegrator` 别名，保持向后兼容

#### 5. `memrl/run/alfworld_rl_runner.py`
- **新增**: `retrieved_skills_per_slot` 列表跟踪每个slot使用的技能
- **新增**: `_get_skill_value()` 辅助方法从技能索引中获取技能Q值
- **修改**: 技能检索时保存技能名称到 `retrieved_skills_per_slot`
- **新增**: 任务完成时自动更新技能Q值并记录变化
  - 在更新前后记录技能Q值
  - 将 `retrieved_skills` 和 `skill_value_changes` 添加到 `completed_experiences`

#### 6. `test/test_alfworld.py`
- **TaskResult 新增字段**: `retrieved_skills`, `skill_value_changes`
- **新增**: `_get_skill_value()` 辅助方法
- **修改**: 任务完成后更新技能Q值并记录变化

#### 7. `configs/rl_alf_config.yaml`
- **新增配置**:
  - `retrieve_general: 1`
  - `retrieve_task_specific: 1`
  - `retrieve_common_mistakes: 1`
  - `value_alpha: 0.5`
  - `value_lambda: 0.5`

### 使用方式

#### 配置示例 (YAML)
```yaml
skill:
  enabled: true
  storage_dir: "skills"
  retrieval_method: "embedding"  # 需要 embedding 才能使用混合评分
  retrieve_general: 1  # 通用技能数量
  retrieve_task_specific: 1  # 任务特定技能数量
  retrieve_common_mistakes: 1  # 常见错误数量
  value_alpha: 0.5  # 学习率
  value_lambda: 0.5  # Q值权重
```

#### 编程调用
```python
# 更新技能Q值
integrator.update_skill_value_by_name("skill-name", success=True)

# 检索技能（按新逻辑）
skills = integrator.retrieve_skills(task_description="...", k=5)
```

### 算法细节

#### Q值更新
- 公式: `Q_new = Q_old + α(r - Q_old)`
- 成功时 r=1: `Q_new = Q_old + α(1 - Q_old)`
- 失败时 r=0: `Q_new = Q_old + α(0 - Q_old) = Q_old(1 - α)`
- 默认 α=0.5: 成功一次 Q从0变为0.5，失败一次 Q从0.5变为0.25

#### 混合检索评分
- 公式: `score = (1 - λ) × sim + λ × Q`
- 每种类型内部按混合评分排序
- 三种类型独立检索后合并
- λ=0 时只考虑语义相似度
- λ=1 时只考虑Q值
- 默认 λ=0.5: 两者权重均衡

## 2026-03-30 - 修复任务类型检测和检索逻辑

### 问题
测试发现所有任务返回相同技能列表，未能根据任务类型差异化检索。原因：
1. `_retrieve_embedding()` 把所有 `task_specific_skills` 扁平化后一起排序，不考虑类型
2. `_detect_task_type()` 的关键词太宽泛，导致误检测（如 "put it in" 触发 pick_and_place）

### 修改的文件

#### `memrl/skills/batch_integration.py`

**1. `_detect_task_type()` 改进**
- 支持 AND 逻辑的关键词组（多条件匹配）
- `pick_and_place` 改为组合匹配：需要同时有 "find/pick/grab" AND "put them/put it"
- 简化 `heat/cool` 关键词，避免误检测

```python
TASK_TYPE_KEYWORDS = {
    # 需要同时满足两组条件
    "pick_and_place": [["find", "pick", "grab"], ["put them", "put it"]],
    "heat": ["heat some", "warm some", "heat it", "warm it"],
    "cool": ["cool some", "cool it", "refrigerate", "chill", "cool the"],
    # ...
}
```

**2. `_retrieve_embedding()` 改进**
- 在计算混合评分前，先调用 `_detect_task_type()` 获取检测到的任务类型
- 只从检测到且存在于技能库中的任务类型检索 `task_specific_skills`
- 避免跨类型污染

```python
# 检测任务类型
detected_types = self._detect_task_type(task_description)

# 过滤 task_specific_skills，只保留存在的类型
available_types = set(task_specific_skills.keys())
valid_types = [t for t in detected_types if t in available_types]

# 只从有效类型中检索
task_specific_flat = []
for task_type, skills in task_specific_skills.items():
    if task_type in valid_types:  # 添加了类型过滤
        for skill in skills:
            task_specific_flat.append(skill)
```

### 效果
| 任务 | 修复前 | 修复后 |
|------|--------|--------|
| "find two toiletpaper and put them in cabinet" | 检索到 cool 类型技能（错误） | 只检索 general + common_mistakes |
| "cool some apple and put it in microwave" | 检索到 cool 类型技能 | 正确检索到 cool 类型技能 |

### 测试命令
```bash
pytest test/test_alfworld.py -v
```

## 2026-03-30 - 修复变量覆盖导致的任务类型错乱

### 问题
虽然添加了类型过滤逻辑，但实际检索时仍然返回错误类型的技能。

### 根因
`_retrieve_embedding()` 中存在变量名覆盖问题：
- 第508行参数 `task_type`（如 `'train/cool'`）
- 第540行循环变量 `for task_type, skills in task_specific_skills.items()`
- 循环结束后 `task_type` 变成 `'heat'`（最后一次迭代的值）
- 第577行 `_normalize_task_type(task_type)` 使用的是被覆盖后的值

### 修复
将循环变量重命名为 `specific_type`，避免覆盖参数：

```python
# 修复前
for task_type, skills in task_specific_skills.items():
    ...
    normalized_type = self._normalize_task_type(task_type)  # task_type 已被覆盖为 'heat'

# 修复后
for specific_type, skills in task_specific_skills.items():
    ...
    normalized_type = self._normalize_task_type(task_type)  # task_type 是正确的参数值
```

### 修复的文件
- `memrl/skills/batch_integration.py`: 重命名两处循环变量

### 验证结果
```
train/cool  → 检索到 execute-cooling-interaction, search-for-hidden-object (cool)
train/heat  → 检索到 ensure-heat-source-accessibility, prioritize-heat-object-search (heat)
pick_and_place → 只有 general + common_mistakes（无对应技能库）
```

## 2026-03-30 - 新技能初始Q值设为0.5

### 问题
新创建的技能初始 Q值为 0.0，导致冷启动问题：
- 高 Q值技能（如 execute-interaction-at-destination Q=0.7）总是被优先检索
- 新技能虽然更相关，但 Q=0.0，检索排名靠后

### 修复
在 `batch_extractor.py` 中创建技能时设置初始 Q值为 0.5：

```python
# general_skills
skill["skill_value"] = 0.5

# task_specific_skills
skill["skill_value"] = 0.5

# common_mistakes
mistake["skill_value"] = 0.5
```

### 修改文件
- `memrl/skills/batch_extractor.py`: 在3处添加初始 Q值设置

---

## 2026-04-13 - 技能遗忘（斩杀线）与合并机制

### 背景

技能库持续增长后需要两种机制：
1. **斩杀线（Culling）**：当技能数量超过上限时，自动删除低价值技能
2. **技能合并（Merging）**：提取新技能时，与现有高度相似的技能合并，避免冗余

### 设计决策

1. **技能唯一标识**：使用 `name` 字段作为唯一标识（而非 `skill_id`）
   - 之前代码中 `skill_id` 字段存在但未被使用
   - 删除 `skill_id` 相关代码，统一使用 `name`
2. **合并触发阈值**：可配置参数，默认 0.85
3. **合并决策**：由 LLM 决定如何合并多个相似技能

### 修改的文件

#### 1. `qskill/skills/skill.py`
- **删除 `skill_id` 字段**：移除 Skill 类的 `skill_id` 属性
- **重命名 `parent_skill_id` → `parent_skill_name`**：保持命名一致性
- **更新 `SkillUpdate`**：将 `skill_id` 改为 `skill_name`
- **更新序列化**：移除 `skill_id`，更新 `parent_skill_name`

#### 2. `qskill/skills/manager.py`
- **方法参数变更**：
  - `update_skill_stats(skill_id)` → `update_skill_stats(name)`
  - `load_skill(skill_id)` → `load_skill(name)`
  - `deprecate_skill(skill_id)` → `deprecate_skill(name)`
  - `update_skill(skill_id, updates)` → `update_skill(name, updates)`
- **`analyze_failure_and_update`**：参数 `skill_ids` → `skill_names`

#### 3. `qskill/skills/analyzer.py`
- **替换引用**：`skill_id=skill.skill_id` → `skill_name=skill.name`

#### 4. `qskill/configs/config.py`
- **SkillConfig 新增字段**：
```python
# 斩杀线配置
enable_culling: bool = False
max_skills: int = 50
cull_threshold: float = 0.3
cull_batch_size: int = 5
cull_min_usage: int = 3

# 合并配置
enable_merging: bool = False
merge_similarity_threshold: float = 0.85
```

#### 5. `qskill/skills/batch_integration.py`
- **新增构造函数参数**：所有 culling 和 merging 相关参数
- **新增 `_cull_low_value_skills()`**：斩杀线实现
  - 按 `skill_value` 升序排序
  - 删除低于 `cull_threshold` 且 `usage_count >= cull_min_usage` 的技能
  - 每次最多删除 `cull_batch_size` 个
  - 在 `trigger_batch_extraction()` 完成后自动调用
- **新增 `_find_mergeable_skills()`**：查找需要合并的技能组
  - 使用 embedding 相似度
  - 返回相似度超过阈值的技能组
- **新增 `_merge_skills_by_name()`**：合并多个技能
  - 收集所有待合并技能详情
  - 调用 LLM 决策合并方案
- **新增 `_llm_merge_skills()`**：LLM 合并决策
  - 发送技能 JSON 给 LLM
  - 返回合并后的技能结构
- **新增 `_compute_merged_stat()`**：统计继承（加权平均）
  - 按 `usage_count` 加权平均 `skill_value`、`success_rate`
- **新增 `_merge_lists()`**：列表去重合并
  - 用于 `failure_scenarios`、`antipatterns`、`constraints`、`trigger_keywords`

#### 6. `qskill/skills/integration.py`
- **传递新参数**：culling 和 merging 配置传递到 BatchSkillIntegrator

#### 7. `configs/rl_alf_config.yaml`
```yaml
skill:
  # ... 原有配置 ...
  # 技能 retention (culling) 配置
  enable_culling: false  # 启用自动斩杀
  max_skills: 50         # 上限
  cull_threshold: 0.3    # 价值阈值
  cull_batch_size: 5     # 每次删除数量
  cull_min_usage: 3      # 最低使用次数
  # 技能合并配置
  enable_merging: false  # 启用合并
  merge_similarity_threshold: 0.85  # 相似度阈值
```

### 统计继承机制

合并后的技能统计计算：
- **skill_value**: 加权平均，按 `usage_count` 权重
- **success_rate**: 加权平均
- **usage_count**: 求和
- **failure_scenarios/antipatterns/constraints/trigger_keywords**: 去重合并
- **steps**: 由 LLM 决定保留哪些

### 触发时机

- **斩杀线**：`trigger_batch_extraction()` 完成后检查，超过 `max_skills` 时触发
- **合并**：`_on_skills_extracted()` 回调中处理，提取新技能后检查相似度

### 使用方式

```yaml
# 启用斩杀线
skill:
  enable_culling: true
  max_skills: 50
  cull_threshold: 0.3

# 启用合并（需要 embedder）
skill:
  enable_merging: true
  merge_similarity_threshold: 0.85
```
