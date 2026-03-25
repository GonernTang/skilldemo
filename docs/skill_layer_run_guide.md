# Skill Layer 运行指南

本文档说明如何在 ALFWorld 基准测试中启用和运行 Skill Layer。

## 1. 环境准备

### 1.1 激活 conda 环境

```bash
conda activate memoryrl
```

### 1.2 配置 API 密钥

编辑 `configs/rl_alf_config.yaml`，填写 LLM 和 Embedding 的 API 密钥：

```yaml
llm:
  api_key: "your-api-key-here"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen3.5-flash"

embedding:
  api_key: "your-api-key-here"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "text-embedding-v4"
```

## 2. 基本运行

### 2.1 运行 WITHOUT Skill Layer（默认）

```bash
python run/run_alfworld.py
```

这将使用原有的 Memory Service，不启用 Skill Layer。

### 2.2 启用 Skill Layer

1. 编辑 `configs/rl_alf_config.yaml`，将 `skill.enabled` 设为 `true`：

```yaml
skill:
  enabled: true  # 启用技能层
  storage_dir: "skills"  # 技能存储目录
  retrieval_method: "llm"  # 检索方法
  extract_threshold: 0.7
  retrieve_k: 3
  auto_extract: true
  auto_analyze_failure: true
```

2. 运行：

```bash
python run/run_alfworld.py
```

### 2.3 强制禁用 Skill Layer

即使配置文件中启用了，也可以通过 CLI 强制禁用：

```bash
python run/run_alfworld.py --disable_skills
```

## 3. Skill Layer 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `enabled` | `false` | 是否启用技能层 |
| `storage_dir` | `"skills"` | 技能 JSON 文件存储目录 |
| `retrieval_method` | `"llm"` | 检索方法：`llm`, `keyword`, `vector`, `hybrid` |
| `extract_threshold` | `0.7` | 提取技能的成功率阈值 |
| `retrieve_k` | `3` | 每次检索返回的技能数量 |
| `auto_extract` | `true` | 是否从成功轨迹自动提取技能 |
| `auto_analyze_failure` | `true` | 是否自动分析失败轨迹并更新技能 |

## 4. 检索方法说明

### 4.1 `llm` (默认，推荐)
- 使用纯 LLM 推理选择最相关的技能
- 不依赖向量嵌入或关键词匹配
- 适合复杂任务理解

### 4.2 `keyword`
- 基于关键词匹配检索技能
- 速度快，但不支持语义理解

### 4.3 `vector`
- 使用向量嵌入计算相似度
- 需要配置 embedder

### 4.4 `hybrid`
- 结合 keyword 过滤和 LLM 重排序
- 兼顾速度和准确性

## 5. 技能存储结构

启用 Skill Layer 后，系统会在 `skills/` 目录下创建以下文件：

```
skills/
├── index.json          # 技能索引文件
├── skill_001.json     # 单个技能文件
├── skill_002.json
└── ...
```

### index.json 结构

```json
{
  "total_count": 10,
  "skills": [
    {
      "skill_id": "skill_001",
      "name": "打开冰箱",
      "task_type": "alfworld/pick",
      "created_at": "2026-03-25T10:00:00"
    }
  ]
}
```

### 单个技能文件结构

```json
{
  "skill_id": "skill_001",
  "name": "打开冰箱",
  "description": "如何在厨房中打开冰箱取物品",
  "task_type": "alfworld/pick",
  "trigger_keywords": ["冰箱", "打开", "冷藏"],
  "applicable_observations": ["in kitchen", "see fridge"],
  "steps": [
    {
      "action": "go to refrigerator",
      "observation_pattern": "in kitchen",
      "reasoning": "先移动到厨房"
    },
    {
      "action": "open object",
      "observation_pattern": "refrigerator",
      "reasoning": "打开冰箱门"
    }
  ],
  "skill_type": "primitive",
  "success_rate": 0.85,
  "usage_count": 10,
  "constraints": ["确保冰箱门可以打开"],
  "antipatterns": [],
  "failure_scenarios": [],
  "deprecated": false
}
```

## 6. 运行时日志

启用 Skill Layer 后，日志中会显示以下信息：

### 技能检索日志
```
INFO - Retrieved skills for task: open fridge - found 3 relevant skills
INFO - Skill injection: 3 skills added to context
```

### 技能提取日志
```
INFO - Slot 0 finished a game. Success: True
INFO - Skill extraction completed for slot 0
```

### 错误日志
```
WARNING - Failed to extract skill from slot 0: <error details>
```

## 7. 查看已提取的技能

技能以 JSON 格式存储在 `skills/` 目录下。可以直接查看：

```bash
# 查看索引
cat skills/index.json | jq

# 查看单个技能
cat skills/skill_001.json | jq
```

## 8. 常见问题

### Q1: 技能没有提取？
- 检查 `skill.enabled` 是否为 `true`
- 检查 `auto_extract` 是否为 `true`
- 确认轨迹是否被标记为成功

### Q2: 技能检索结果为空？
- 检查 `skills/` 目录下是否有技能文件
- 确认 `retrieval_method` 配置正确
- 查看日志中的检索信息

### Q3: LLM 检索失败？
- 检查 LLM API 配置是否正确
- 检查 API 密钥是否有效
- 查看日志中的错误信息

### Q4: 如何清空所有技能？
```bash
rm -rf skills/
mkdir skills
```

## 9. 性能考虑

- **首次运行**: 启用 Skill Layer 会增加每次 API 调用的延迟（检索+提取）
- **存储**: 技能文件占用空间很小（每个技能约 1-2KB）
- **检索开销**: LLM 检索每次约增加 0.5-1 秒延迟

## 10. 完整配置示例

```yaml
# configs/rl_alf_config.yaml

llm:
  provider: "openai"
  api_key: "your-key"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen3.5-flash"

embedding:
  provider: "openai"
  api_key: "your-key"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "text-embedding-v4"

skill:
  enabled: true
  storage_dir: "skills"
  retrieval_method: "llm"
  extract_threshold: 0.7
  retrieve_k: 3
  auto_extract: true
  auto_analyze_failure: true
```
