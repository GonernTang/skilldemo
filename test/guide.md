  脚本已创建在 test/test_alfworld.py，功能如下：

  功能特性
  ┌──────────────┬───────────────────────────────────────────┐
  │     功能     │                   说明                    │
  ├──────────────┼───────────────────────────────────────────┤
  │ 随机选任务   │ 从 ALFWorld 训练集中随机选择 N 个任务执行 │
  ├──────────────┼───────────────────────────────────────────┤
  │ 实时轨迹打印 │ 每一步的 Action 和 Observation 都实时打印 │
  ├──────────────┼───────────────────────────────────────────┤
  │ 执行结果     │ 输出成功/失败状态                         │
  ├──────────────┼───────────────────────────────────────────┤
  │ 完整轨迹     │ 记录所有 action-observation 对            │
  ├──────────────┼───────────────────────────────────────────┤
  │ 技能提取     │ 成功后调用 skill integrator 提取技能      │
  ├──────────────┼───────────────────────────────────────────┤
  │ Token 消耗   │ 从 token_usage.jsonl 读取并统计           │
  └──────────────┴───────────────────────────────────────────┘
  使用方法

  # 默认配置：随机选5个任务
  python test/test_alfworld.py

  # 指定任务数量
  python test/test_alfworld.py --num_tasks 3

  # 指定随机种子
  python test/test_alfworld.py --seed 123 --num_tasks 10

  # 禁用记忆系统（快速测试）
  python test/test_alfworld.py --disable_memory

  # 禁用技能层
  python test/test_alfworld.py --disable_skills

  # 使用指定配置文件
  python test/test_alfworld.py --config configs/rl_alf_config.yaml

  输出内容

  1. 实时打印：每个任务的 step-by-step 执行过程
  2. 最终汇总：
    - 成功率、任务数、耗时
    - Token 消耗统计（prompt/completion/total）
  3. 详细 JSON：test/test_results.json 包含每个任务的完整轨迹

  前置依赖

  需要先安装项目依赖：
  pip install -r requirements.txt

  以及 ALFWorld 环境（如果尚未安装）。