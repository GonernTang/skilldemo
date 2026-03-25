"""Skill extraction from successful trajectories using LLM."""

import hashlib
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from memrl.providers.base import BaseLLM
from memrl.skills.skill import Skill, SkillStep


class SkillExtractor:
    """Extracts reusable skills from successful task trajectories."""

    def __init__(
        self,
        llm: BaseLLM,
        min_steps: int = 2,
        max_steps: int = 10,
    ):
        """Initialize the SkillExtractor.

        Args:
            llm: LLM provider for refinement.
            min_steps: Minimum number of action-observation pairs to extract.
            max_steps: Maximum number of steps to include in a skill.
        """
        self.llm = llm
        self.min_steps = min_steps
        self.max_steps = max_steps

    def extract(
        self,
        trajectory: List[Dict[str, str]],
        task_description: str,
        task_type: str,
        source_trajectory_id: Optional[str] = None,
    ) -> Optional[Skill]:
        """Extract a Skill from a successful trajectory.

        Args:
            trajectory: Agent execution trajectory as message list.
            task_description: Description of the task.
            task_type: Type/category of the task.
            source_trajectory_id: ID of the source trajectory.

        Returns:
            Extracted Skill object, or None if extraction failed.
        """
        # Step 1: Parse trajectory into action-observation pairs
        action_obs_pairs = self._parse_trajectory(trajectory)
        if len(action_obs_pairs) < self.min_steps:
            return None

        # Step 2: LLM refine to extract skill information
        extracted = self._llm_refine(
            action_obs_pairs=action_obs_pairs,
            task_description=task_description,
            task_type=task_type,
        )

        if not extracted:
            return None

        # Step 3: Build Skill object
        return self._build_skill(
            extracted=extracted,
            task_description=task_description,
            task_type=task_type,
            source_trajectory_id=source_trajectory_id,
        )

    def _parse_trajectory(
        self,
        trajectory: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """Parse trajectory into action-observation pairs.

        Args:
            trajectory: Message list with assistant/user roles.

        Returns:
            List of dicts with 'action' and 'observation' keys.
        """
        pairs = []
        current_action = None

        for msg in trajectory:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "assistant":
                # Extract Action
                if "Action:" in content:
                    action = content.split("Action:")[-1].strip()
                    current_action = action
            elif role == "user" and content.startswith("Observation:") and current_action:
                # Extract Observation
                observation = content.replace("Observation:", "").strip()
                pairs.append({
                    "action": current_action,
                    "observation": observation,
                })
                current_action = None

        return pairs

    def _llm_refine(
        self,
        action_obs_pairs: List[Dict[str, str]],
        task_description: str,
        task_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to refine action-observation pairs into skill information.

        Args:
            action_obs_pairs: Parsed action-observation pairs.
            task_description: Original task description.
            task_type: Task type/category.

        Returns:
            Dict with skill fields, or None if LLM refinement failed.
        """
        # Format action-observation pairs for prompt
        steps_text = "\n".join([
            f"Step {i+1}:\n  Action: {p['action']}\n  Observation: {p['observation']}"
            for i, p in enumerate(action_obs_pairs)
        ])

        prompt = f"""你是一个任务分解专家。请从以下成功执行的轨迹中提取可复用的技能模式。

## 任务描述
{task_description}

## 任务类型
{task_type}

## 执行轨迹
{steps_text}

## 你的任务
1. 分析这个轨迹，识别核心的动作步骤（可能需要过滤一些噪音步骤）
2. 为每个核心步骤生成:
   - action: 原始动作
   - observation_pattern: 触发此动作的观察条件（简洁描述）
   - reasoning: 为什么要执行这个动作
3. 生成技能的元信息:
   - name: 技能名称（简洁，描述技能做什么）
   - description: 技能描述（描述功能和使用场景，2-3句话）
   - trigger_keywords: 触发关键词列表（5-10个，用于检索）
   - applicable_observations: 适用观察条件列表（3-5个）
4. 判断 skill_type:
   - "primitive": 单一技能，不可再分
   - "composite": 组合技能，可由多个子技能组成

## 输出格式 (JSON)
{{
  "name": "技能名称",
  "description": "技能描述",
  "trigger_keywords": ["关键词1", "关键词2", ...],
  "applicable_observations": ["观察1", "观察2", ...],
  "skill_type": "primitive 或 composite",
  "steps": [
    {{
      "action": "原始动作",
      "observation_pattern": "触发条件",
      "reasoning": "动作原因"
    }},
    ...
  ]
}}

请仅输出 JSON，不要有其他内容。
"""

        response = self.llm.generate([{"role": "user", "content": prompt}])

        # Parse JSON response
        try:
            extracted = json.loads(response)
            return extracted
        except json.JSONDecodeError:
            return None

    def _build_skill(
        self,
        extracted: Dict[str, Any],
        task_description: str,
        task_type: str,
        source_trajectory_id: Optional[str],
    ) -> Skill:
        """Build a Skill object from LLM-refined data.

        Args:
            extracted: Refined skill data from LLM.
            task_description: Original task description.
            task_type: Task type/category.
            source_trajectory_id: Source trajectory ID.

        Returns:
            Constructed Skill object.
        """
        # Generate unique skill ID
        skill_id = f"skill_{int(time.time())}_{hashlib.md5(task_description.encode()).hexdigest()[:8]}"

        # Build steps
        steps = []
        for step_data in extracted.get("steps", []):
            steps.append(SkillStep(
                action=step_data.get("action", ""),
                observation_pattern=step_data.get("observation_pattern", ""),
                reasoning=step_data.get("reasoning", ""),
            ))

        return Skill(
            skill_id=skill_id,
            name=extracted.get("name", task_description[:50]),
            description=extracted.get("description", task_description),
            task_type=task_type,
            trigger_keywords=extracted.get("trigger_keywords", []),
            applicable_observations=extracted.get("applicable_observations", []),
            steps=steps,
            skill_type=extracted.get("skill_type", "primitive"),
            parent_skill_id=None,
            success_rate=1.0,
            usage_count=0,
            last_used_at=None,
            created_at=datetime.utcnow().isoformat(),
            source_trajectory_id=source_trajectory_id,
        )

    def batch_extract(
        self,
        trajectories: List[Tuple[List[Dict[str, str]], str, str]],
        success_threshold: float = 0.7,
    ) -> List[Skill]:
        """Extract skills from multiple successful trajectories.

        Args:
            trajectories: List of (trajectory, task_description, task_type) tuples.
            success_threshold: Threshold for batch extraction.

        Returns:
            List of extracted Skill objects.
        """
        # Group by task type
        from collections import defaultdict
        grouped = defaultdict(list)
        for traj, desc, ttype in trajectories:
            grouped[ttype].append((traj, desc))

        all_skills = []

        for task_type, items in grouped.items():
            if len(items) < 3:
                continue

            # Merge multiple trajectories into one skill
            merged_skill = self._merge_trajectories(
                trajectories=[t[0] for t in items],
                task_description=items[0][1],
                task_type=task_type,
            )
            if merged_skill:
                all_skills.append(merged_skill)

        return all_skills

    def _merge_trajectories(
        self,
        trajectories: List[List[Dict[str, str]]],
        task_description: str,
        task_type: str,
    ) -> Optional[Skill]:
        """Merge multiple similar trajectories into a generalizable skill.

        Args:
            trajectories: List of successful trajectories.
            task_description: Common task description.
            task_type: Task type/category.

        Returns:
            Merged Skill object, or None if merge failed.
        """
        trajectories_text = ""
        for i, traj in enumerate(trajectories):
            pairs = self._parse_trajectory(traj)
            trajectories_text += f"\n轨迹 {i+1}:\n"
            for p in pairs:
                trajectories_text += f"  - Action: {p['action']}, Obs: {p['observation'][:50]}...\n"

        prompt = f"""你是一个任务分解专家。请分析以下多个相似的成功轨迹，找出它们的共同模式，提炼出一个可复用的通用技能。

## 任务描述
{task_description}

## 任务类型
{task_type}

## 多个成功轨迹
{trajectories_text}

## 你的任务
1. 分析这些轨迹的共同模式
2. 提炼出适用于所有轨迹的核心动作步骤
3. 生成一个通用的、可复用的技能

## 输出格式 (JSON)
{{
  "name": "通用技能名称",
  "description": "通用技能描述",
  "trigger_keywords": ["关键词1", "关键词2", ...],
  "applicable_observations": ["观察1", "观察2", ...],
  "skill_type": "primitive 或 composite",
  "steps": [
    {{
      "action": "通用动作（抽象后的）",
      "observation_pattern": "触发条件",
      "reasoning": "动作原因"
    }},
    ...
  ]
}}

请仅输出 JSON，不要有其他内容。
"""

        response = self.llm.generate([{"role": "user", "content": prompt}])

        try:
            extracted = json.loads(response)
            return self._build_skill(
                extracted=extracted,
                task_description=task_description,
                task_type=task_type,
                source_trajectory_id=None,
            )
        except json.JSONDecodeError:
            return None


class ExtractionTrigger:
    """Determines when to extract a new skill from a trajectory."""

    def __init__(self, config: "SkillConfig"):
        """Initialize the trigger.

        Args:
            config: Skill configuration object.
        """
        self.config = config
        self.extractor = SkillExtractor(llm=config.llm)

    def should_extract(
        self,
        task_type: str,
        trajectory: List[Dict[str, str]],
        success: bool,
        current_success_rate: float = 0.0,
    ) -> Tuple[bool, str]:
        """Determine if a skill should be extracted.

        Args:
            task_type: Type of the task.
            trajectory: Execution trajectory.
            success: Whether the task succeeded.
            current_success_rate: Current success rate for this task type.

        Returns:
            Tuple of (should_act, action_type).
            action_type is "extract_new" | "none".
        """
        if not success:
            return False, "none"

        if not self.config.auto_extract:
            return False, "none"

        if self._has_enough_steps(trajectory):
            return True, "extract_new"

        return False, "none"

    def _has_enough_steps(self, trajectory: List[Dict[str, str]]) -> bool:
        """Check if trajectory has enough action steps.

        Args:
            trajectory: Execution trajectory.

        Returns:
            True if trajectory has enough steps for extraction.
        """
        action_count = sum(
            1 for msg in trajectory
            if msg.get("role") == "assistant" and "Action:" in msg.get("content", "")
        )
        return action_count >= self.extractor.min_steps


class SkillConfig:
    """Configuration for skill extraction and management."""

    def __init__(
        self,
        llm: BaseLLM,
        storage_dir: str = "skills",
        retrieval_method: str = "llm",
        extract_threshold: float = 0.7,
        retrieve_k: int = 3,
        auto_extract: bool = True,
        auto_analyze_failure: bool = True,
        enabled: bool = True,
    ):
        """Initialize SkillConfig.

        Args:
            llm: LLM provider for extraction and retrieval.
            storage_dir: Directory for skill storage.
            retrieval_method: Method for retrieval (llm, keyword, vector, hybrid).
            extract_threshold: Success rate threshold for extraction.
            retrieve_k: Number of skills to retrieve.
            auto_extract: Whether to automatically extract from success.
            auto_analyze_failure: Whether to automatically analyze failures.
            enabled: Whether the skill layer is enabled.
        """
        self.llm = llm
        self.storage_dir = storage_dir
        self.retrieval_method = retrieval_method
        self.extract_threshold = extract_threshold
        self.retrieve_k = retrieve_k
        self.auto_extract = auto_extract
        self.auto_analyze_failure = auto_analyze_failure
        self.enabled = enabled
