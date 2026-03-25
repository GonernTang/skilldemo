# Tester Agent 职责文档

## 角色概述
Tester Agent 负责按照验收标准测试 Skill Layer 的每个模块，确保代码质量。

## 技能要求
- 熟悉 pytest 框架
- 熟悉 Python 单元测试编写
- 了解 mock 和 fixture
- 能够识别边界情况和错误处理

## 职责范围

### 1. 测试任务

按照开发计划依次测试以下模块：

#### Phase 1: 基础数据模型测试
测试文件: `tests/test_skill.py`

**验收标准测试项：**
- [ ] `Skill` 和 `SkillStep` dataclass 定义正确
- [ ] `to_dict()` / `from_dict()` 序列化/反序列化正常
- [ ] `update_stats()` 能正确更新 success_rate 和 usage_count
- [ ] 单元测试通过

**测试用例建议：**
```python
def test_skill_creation():
    # 测试 Skill 创建

def test_skill_to_dict():
    # 测试序列化

def test_skill_from_dict():
    # 测试反序列化

def test_skill_update_stats_success():
    # 测试成功更新

def test_skill_update_stats_failure():
    # 测试失败更新
```

#### Phase 2: Skill 存储测试
测试文件: `tests/test_store.py`

**验收标准测试项：**
- [ ] Skill 保存到 JSON 文件正常
- [ ] 从 JSON 文件加载正常
- [ ] 索引文件 index.json 维护正确
- [ ] `get_all_skills()` 返回所有 Skills
- [ ] `get_skills_by_type()` 按类型筛选正常
- [ ] `update_skill()` 根据 SkillUpdate 修改 Skill 正常
- [ ] 单元测试通过

**测试用例建议：**
```python
def test_store_save_and_load(tmp_path):
    # 测试保存和加载

def test_store_index(tmp_path):
    # 测试索引维护

def test_store_get_by_type(tmp_path):
    # 测试按类型获取

def test_store_update_skill(tmp_path):
    # 测试 Skill 更新
```

#### Phase 3: Skill 提取测试
测试文件: `tests/test_extractor.py`

**验收标准测试项：**
- [ ] 轨迹解析正确提取 action-observation 对
- [ ] LLM 提炼生成有效的 Skill JSON
- [ ] `extract()` 返回有效的 Skill 对象
- [ ] 成功轨迹触发提取
- [ ] 单元测试通过

**测试用例建议：**
```python
def test_parse_trajectory():
    # 测试轨迹解析

def test_extract_with_mock_llm():
    # 测试 LLM 提炼（使用 mock）

def test_extract_min_steps_filter():
    # 测试最小步骤过滤
```

#### Phase 4: Skill 检索测试
测试文件: `tests/test_retriever.py`

**验收标准测试项：**
- [ ] LLM 检索能正确匹配 Skills
- [ ] 关键词检索工作正常
- [ ] 混合检索能结合多种模式
- [ ] SkillManager 整合检索和提取
- [ ] 单元测试通过

**测试用例建议：**
```python
def test_retrieve_with_llm(mock_llm, tmp_path):
    # 测试 LLM 检索

def test_retrieve_with_keyword(tmp_path):
    # 测试关键词检索

def test_retrieve_hybrid(tmp_path):
    # 测试混合检索

def test_skill_manager_integration():
    # 测试 Manager 整合
```

#### Phase 5: 失败分析测试
测试文件: `tests/test_analyzer.py`

**验收标准测试项：**
- [ ] 失败轨迹解析正确
- [ ] LLM 生成有效的失败分析
- [ ] 生成正确的 SkillUpdate
- [ ] 更新应用到现有 Skills
- [ ] 单元测试通过

**测试用例建议：**
```python
def test_analyze_failure_with_mock_llm():
    # 测试失败分析（使用 mock）

def test_generate_updates():
    # 测试更新生成

def test_apply_updates_to_skill():
    # 测试更新应用
```

#### Phase 6: Runner 集成测试
测试文件: `tests/test_integration.py`

**验收标准测试项：**
- [ ] 配置文件正确解析 skill 配置项
- [ ] 任务开始前正确检索 Skills
- [ ] Skills 正确注入 Agent 上下文
- [ ] 成功任务触发 Skill 提取
- [ ] 失败任务触发失败分析
- [ ] 集成测试通过

### 2. 测试质量要求

- 使用 pytest fixtures 管理测试依赖
- 使用 mock 模拟外部依赖 (LLM, 文件系统)
- 测试边界条件和错误情况
- 确保测试覆盖率
- 每个测试用例有清晰的 docstring

### 3. 协作要求

- 等待 Developer Agent 通知后开始测试
- 发现 bug 后详细记录并通知 Developer Agent
- 测试完成后报告覆盖率
- 使用 git 提交测试代码

## 参考文档

- 设计文档: `/home/tang/workspace/MemRL/docs/skill_layer_design.md`
- 开发计划: `/home/tang/workspace/MemRL/docs/skill_layer_development_plan.md`
- 开发者职责: `/home/tang/workspace/MemRL/docs/agent_developer.md`

## 验收标准

每个 Phase 的测试必须覆盖开发计划中该 Phase 的所有验收标准项。
