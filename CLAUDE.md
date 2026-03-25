# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

MemRL 是一个基于情节记忆的运行时强化学习系统，通过"构建-检索-更新"三阶段记忆管理策略实现智能体的自我演进。核心特点是不更新模型权重，而是通过记忆管理实现持续改进。

## 开发命令

```bash
# 安装依赖
pip install -r requirements.txt

# 代码格式化
black memrl/

# Linting
ruff check memrl/

# 类型检查
mypy memrl/

# 运行测试
pytest

# 运行特定测试
pytest tests/test_specific.py
```

## 架构设计

### 三层架构

```
Runner 层 (run/run_*.py)
    └── 编排 agent、env、memory service 之间的交互
    └── 多轮训练循环，检查点管理
         ↓
Agent 层 (memrl/agent/)
    └── BaseAgent: reset, act, get_trajectory 接口
    └── MempAgent: 基于 LLM 的无状态智能体
         ↓
Memory Service 层 (memrl/service/)
    └── 集成 MemOS 的核心记忆管理
    └── Build/Retrieve/Update 策略实现
```

### 三阶段记忆策略

系统通过策略组合实现记忆管理（共 27 种组合）：

| 阶段 | 策略 | 说明 |
|------|------|------|
| **Build** | `trajectory` | 存储完整轨迹 |
| | `script` | 仅存储 LLM 生成的高级脚本 |
| | `proceduralization` | 同时存储脚本和轨迹（推荐） |
| **Retrieve** | `random` | 随机采样 |
| | `query` | 使用任务描述向量检索 |
| | `avefact` | 关键词向量平均（推荐） |
| **Update** | `vanilla` | 添加所有轨迹 |
| | `validation` | 仅添加成功轨迹 |
| | `adjustment` | 失败时反思并调整现有记忆（推荐） |

### 值驱动 RL 组件

当 `experiment.enable_value_driven=true` 时启用：

- **ValueAwareSelector**: 基于 Q 值和 ε-greedy 从 Top-K 中选择记忆
- **QValueUpdater**: Q-learning 更新持久化到 MemOS metadata
- **未知检测**: 当相似度低于 `tau` 时触发 Zero-Shot 回退

关键参数：
- `tau`: 未知检测阈值
- `alpha`: Q 学习步长
- `epsilon`: ε-greedy 探索概率
- `sim_threshold`: 检索过滤阈值

## 核心模块依赖

```
memrl/service/memory_service.py  (核心入口)
    ├── strategies.py       (策略枚举)
    ├── builders.py         (构建策略实现)
    ├── retrievers.py       (检索策略实现)
    ├── updater.py          (更新策略实现)
    ├── value_driven.py     (RL 组件)
    ├── keyer.py            (查询键生成)
    └── memos (MemOS 框架)

memrl/providers/
    ├── llm.py              (OpenAI LLM, 含重试逻辑)
    └── embedding.py       (Embedding 提供者)

memrl/configs/config.py    (Pydantic 配置模型)

memrl/agent/memp_agent.py   (智能体实现)
```

## 配置管理

所有 benchmark 配置使用 YAML 文件在 `configs/` 目录下：

```yaml
llm:
  api_key: your_api_key
  model: gpt-4o
  base_url: optional_openai_compatible_endpoint

embedding:
  api_key: your_api_key
  model: text-embedding-3-small

memory:
  build_strategy: proceduralization
  retrieve_strategy: avefact
  update_strategy: adjustment
  k_retrieve: 5

experiment:
  enable_value_driven: true
  output_dir: results/
```

## 运行 Benchmark

```bash
# BigCodeBench
python run/run_bcb.py --config configs/rl_bcb_config.yaml --split instruct --epochs 10

# HLE
python run/run_hle.py --config configs/rl_hle_config.yaml --train /path/to/hle_train.parquet

# ALFWorld
python run/run_alfworld.py --config configs/rl_alf_config.yaml

# Lifelong Agent Bench
python run/run_llb.py
```

## 常见问题

**CXXABI_1.3.15 not found 错误**：
```bash
export LD_PRELOAD="$CONDA_PREFIX/lib/libstdc++.so.6${LD_PRELOAD:+:$LD_PRELOAD}"
```
