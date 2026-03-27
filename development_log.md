# MemRL 开发日志

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
