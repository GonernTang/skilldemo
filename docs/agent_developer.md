# Developer Agent 职责文档

## 角色概述
Developer Agent 负责按照设计文档实现 Skill Layer 的所有模块。

## 技能要求
- 熟悉 Python dataclass 和类型提示
- 熟悉 JSON 文件操作
- 了解 LLM API 调用
- 了解现有 MemRL 架构（Runner, Agent, MemoryService）

## 职责范围

### 1. 核心开发任务

按照开发计划依次实现以下模块：

#### Phase 1: 基础数据模型
- 创建 `memrl/skills/skill.py`
- 实现 `SkillStep` dataclass
- 实现 `Skill` dataclass（含 to_dict, from_dict, update_stats 等方法）
- 实现 `SkillUpdate` dataclass

#### Phase 2: Skill 存储
- 创建 `memrl/skills/store.py`
- 实现 `SkillStore` 类
- 实现基础 CRUD 操作 (save, load, delete)
- 实现索引管理 (_load_index, _update_index)
- 实现批量操作 (get_all_skills, get_skills_by_type)

#### Phase 3: Skill 提取
- 创建 `memrl/skills/extractor.py`
- 实现 `SkillExtractor` 类
- 实现轨迹解析 (_parse_trajectory)
- 实现 LLM 提炼 (_llm_refine)
- 实现提取触发条件 (ExtractionTrigger)

#### Phase 4: Skill 检索
- 创建 `memrl/skills/retriever.py`
- 实现 `SkillRetriever` 类
- 实现纯 LLM 推理检索 (_retrieve_with_llm)
- 实现关键词检索 (_retrieve_with_keyword)
- 实现向量检索 (_retrieve_with_vector)
- 实现混合检索 (_retrieve_hybrid)
- 创建 `memrl/skills/manager.py`
- 实现 `SkillManager` 类，整合所有功能

#### Phase 5: 失败分析
- 创建 `memrl/skills/analyzer.py`
- 实现 `FailureAnalyzer` 类
- 实现失败轨迹分析 (_analyze_failure)
- 实现 Skill 更新生成 (_generate_skill_update)
- 更新 SkillManager 添加 analyze_failure_and_update 方法

#### Phase 6: Runner 集成
- 修改 `memrl/run/alfworld_rl_runner.py`
- 添加 Skill 配置项支持
- 在任务执行流程中集成 Skill 检索和提取
- 修改 `memrl/agent/memp_agent.py`
- _construct_messages 添加 skills 参数
- 添加 _format_skills 方法

### 2. 代码质量要求

- 使用 type hints
- 遵守 black 格式化 (line-length=88)
- 遵守 ruff linting 规则
- 编写 docstring
- 每个类和方法有清晰的注释

### 3. 协作要求

- 完成每个 Phase 后通知 Tester Agent 进行测试
- 收到测试反馈后及时修复 bug
- 使用 git 提交记录开发进度
- 提交信息遵循规范: `type: description`

## 参考文档

- 设计文档: `/home/tang/workspace/MemRL/docs/skill_layer_design.md`
- 开发计划: `/home/tang/workspace/MemRL/docs/skill_layer_development_plan.md`

## 验收标准

每个 Phase 完成后，需要满足开发计划中的验收标准才能交付测试。
