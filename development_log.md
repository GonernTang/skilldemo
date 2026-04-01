# MemRL 开发日志

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
