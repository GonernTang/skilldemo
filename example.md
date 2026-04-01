参考这个项目的skill层，删除原有skill层，仿照他这个重新设计
### 技能系统详解

MetaClaw 的技能系统由 `SkillManager` 和 `SkillEvolver` 两个核心组件构成，支持技能的创建、演化、检索全生命周期管理。

---

#### 技能文件格式

技能文件位于 `~/.metaclaw/skills/<skill-name>/SKILL.md`：

```markdown
---
name: debug-systematically
description: Use when diagnosing a bug or error
category: coding
---

## Debug Systematically

**Process:**
1. **Reproduce** the bug with the smallest possible input.
2. **Isolate** — narrow down which component/function causes it.
3. **Hypothesize** — form a specific, falsifiable hypothesis.
4. **Test** — verify or disprove the hypothesis with a minimal experiment.
5. **Fix** — address the root cause, not just the symptom.
6. **Verify** — re-run the failing test and related tests.

**Anti-patterns:**
- Changing multiple things at once and not knowing what fixed it.
- Ignoring related test failures.
```

**字段说明**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 技能名称，小写字母、数字、连字符组成（如 `debug-systematically`） |
| `description` | 是 | 一句话描述，用于检索时的匹配判断 |
| `category` | 否 | 类别，默认 `general` |

**有效类别**：`general`、`coding`、`research`、`data_analysis`、`security`、`communication`、`automation`、`agentic`、`productivity`、`common_mistakes`

**技能内容规范**：
- 6-15 行可执行的 Markdown 内容
- 包含编号步骤或要点
- 包含具体示例或代码片段（适用时）
- 包含 **Anti-pattern** 反面模式说明

---

#### 技能存储结构

运行时技能在内存中以 JSON 结构存储，由 `SkillManager` 加载后转换：

```json
{
  "general_skills": [
    {
      "name": "clarify-ambiguous-requests",
      "description": "Use when the user's request is ambiguous...",
      "content": "## Clarify Ambiguous Requests\n\nWhen the task...",
      "category": "general"
    }
  ],
  "task_specific_skills": {
    "coding": [...],
    "research": [...],
    "data_analysis": [...],
    "security": [...],
    "communication": [...],
    "automation": [...],
    "agentic": [...],
    "productivity": [...]
  },
  "common_mistakes": [
    {
      "name": "avoid-acting-on-assumptions",
      "description": "Common mistake: proceeding with assumptions...",
      "content": "## Avoid Acting on Assumptions\n\n...",
      "category": "common_mistakes"
    }
  ]
}
```

---

#### 技能检索

技能在 API 代理服务器拦截 LLM 请求时自动检索并注入。

**检索入口**：`SkillManager.retrieve(task_description, top_k=6)`

**检索模式**（可配置 `skills.retrieval_mode`）：

**1. 模板匹配模式** (`template`，默认)：
- 通过关键词检测任务类型（`_detect_task_type`）
- 根据类型从对应类别选取技能
- 返回：`general_skills` (top_k) + `task_specific_skills` (按类型) + `common_mistakes` (top 5)

**2. 嵌入向量模式** (`embedding`)：
- 使用 SentenceTransformer 将任务描述和技能描述编码为向量
- 通过余弦相似度选取最相关的技能
- 需要安装 `sentence-transformers` 依赖

**注入方式**：
检索到的技能通过 `format_for_conversation()` 格式化为 Markdown，追加到系统提示末尾：

```markdown
## Active Skills

### clarify-ambiguous-requests
_Use when the user's request is ambiguous..._

## Clarify Ambiguous Requests

When the task or constraint is unclear, do not guess — ask.
...
```

---

#### 技能创建

**方式一：手动创建**

用户直接在 `~/.metaclaw/skills/<skill-name>/SKILL.md` 创建文件，目录结构：

```
~/.metaclaw/skills/
├── debug-systematically/
│   └── SKILL.md
├── git-workflow/
│   └── SKILL.md
└── clarify-ambiguous-requests/
    └── SKILL.md
```

**方式二：自动进化（SkillEvolver）**

1. 收集失败轨迹
2. 构建分析 Prompt：
   - 失败对话上下文（最后 600 字符）
   - 助手响应前 500 字符
   - 现有技能列表（避免重复）
3. 调用 LLM（默认 `gpt-5.2`，可通过 `SKILL_EVOLVER_MODEL` 配置）生成 1-3 个新技能
4. 解析 LLM 返回的 JSON，验证字段完整性
5. 分配 `dyn-NNN` 格式名称（如 LLM 返回的名称不合规）
6. 调用 `SkillManager.add_skills()` 写入 skills 目录

**环境变量**：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | 必填 | LLM API Key |
| `OPENAI_BASE_URL` | `https://openai-api.shenmishajing.workers.dev/v1` | API 地址 |
| `SKILL_EVOLVER_MODEL` | `gpt-5.2` | 进化器模型 |

**进化历史**：每次进化记录追加到 `evolution_history.jsonl`：

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "num_failures_analyzed": 6,
  "num_skills_generated": 2,
  "skill_names": ["verify-path-existence", "dyn-001"],
  "skills": [
    {
      "name": "verify-path-existence",
      "category": "coding",
      "description": "Use when the user provides a path...",
      "content": "## Verify Path Existence\n\n..."
    }
  ],
  "failure_prompts": ["...failure prompt excerpt..."]
}
```

---

#### 技能演化流程图

```
┌─────────────────────────────────────────────────────────────┐
│                     RL Training Loop                         │
│  ┌──────────┐    ┌──────────┐    ┌───────────────────────┐  │
│  │ 收集批次  │ -> │ 计算 reward │ -> │ 成功率 < 40%?       │  │
│  └──────────┘    └──────────┘    └─────────┬─────────────┘  │
│                                            │ 是             │
│                                            v                │
│                          ┌──────────────────────────────┐  │
│                          │   SkillEvolver.evolve()      │  │
│                          │   1. 收集失败样本 (≤6)        │  │
│                          │   2. 构建分析 Prompt          │  │
│                          │   3. 调用 LLM 生成新技能      │  │
│                          │   4. 解析验证 JSON            │  │
│                          │   5. 分配名称                  │  │
│                          └──────────────┬───────────────┘  │
│                                         v                  │
│                          ┌──────────────────────────────┐  │
│                          │  SkillManager.add_skills()   │  │
│                          │  写入 ~/.metaclaw/skills/    │  │
│                          └──────────────┬───────────────┘  │
│                                         v                  │
│                          ┌──────────────────────────────┐  │
│                          │  skill_generation++ (版本号) │  │
│                          │  RL trainer 丢弃旧样本        │  │
│                          └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

#### 技能检索流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    API 代理服务器 (api_server.py)           │
│                                                              │
│  1. 收到 LLM API 请求                                         │
│  2. 提取对话内容作为 task_description                          │
│  3. 调用 skill_manager.retrieve(task_description, top_k=6)    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              SkillManager.retrieve()                   │  │
│  │                                                        │  │
│  │  模板模式 (template):                                   │  │
│  │  ┌──────────────────┐  ┌────────────────────────────┐  │  │
│  │  │ _detect_task_type │  │ 从 general_skills 取 top_k │  │  │
│  │  │  (关键词匹配任务)   │  │ 从 task_specific 取对应类别 │  │  │
│  │  └──────────────────┘  └────────────────────────────┘  │  │
│  │                                                        │  │
│  │  嵌入模式 (embedding):                                  │  │
│  │  ┌──────────────────────────────┐  ┌───────────────┐  │  │
│  │  │ SentenceTransformer 编码      │  │ 余弦相似度排序  │  │  │
│  │  │ task + skills                 │  │ 选取 top_k    │  │  │
│  │  └──────────────────────────────┘  └───────────────┘  │  │
│  │                                                        │  │
│  │  始终追加: common_mistakes (最多 5 条)                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          v                                  │
│  4. format_for_conversation() 格式化为 Markdown             │
│  5. 追加到原系统提示末尾                                      │
│  6. 转发增强后的请求给上游 LLM                                │
└─────────────────────────────────────────────────────────────┘
```
