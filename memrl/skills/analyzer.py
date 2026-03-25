"""Failure analysis for skill improvement from failed trajectories."""

import json
from typing import Any, Dict, List, Optional, Tuple

from memrl.providers.base import BaseLLM
from memrl.skills.skill import Skill, SkillStep, SkillUpdate


class FailureAnalyzer:
    """Analyzes failed trajectories to generate skill updates."""

    def __init__(self, llm: BaseLLM):
        """Initialize the FailureAnalyzer.

        Args:
            llm: LLM provider for failure analysis.
        """
        self.llm = llm

    def analyze(
        self,
        failed_trajectory: List[Dict[str, Any]],
        task_description: str,
        task_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Analyze a failed trajectory to understand failure causes.

        Args:
            failed_trajectory: The failed execution trajectory.
            task_description: Description of the task.
            task_type: Type/category of the task.

        Returns:
            Failure analysis dict, or None if analysis failed.
        """
        pairs = self._parse_trajectory(failed_trajectory)
        failure_point = pairs[-1] if pairs else None

        prompt = f"""你是一个失败分析专家。请分析以下失败轨迹，找出失败原因。

## 任务描述
{task_description}

## 任务类型
{task_type}

## 执行轨迹
{self._format_pairs(pairs)}

## 失败点
{failure_point}

## 输出格式 (JSON)
{{
  "failure_step": 失败步骤索引,
  "failure_action": "失败的动作",
  "failure_reason": "wrong_action | wrong_order | missing_prerequisite | environment_error",
  "failure_detail": "详细描述",
  "lesson": "教训总结（以后应该怎么做）",
  "avoid_keywords": ["应该避免的关键词1", "关键词2"],
  "correct_approach": "正确的做法应该是什么"
}}

请仅输出 JSON。
"""

        response = self.llm.generate([{"role": "user", "content": prompt}])

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return None

    def _parse_trajectory(
        self,
        trajectory: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """Parse trajectory into action-observation pairs.

        Args:
            trajectory: Message list with roles.

        Returns:
            List of action-observation dicts.
        """
        pairs = []
        current_action = None

        for msg in trajectory:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "assistant":
                if "Action:" in content:
                    action = content.split("Action:")[-1].strip()
                    current_action = action
            elif role == "user" and content.startswith("Observation:") and current_action:
                observation = content.replace("Observation:", "").strip()
                pairs.append({
                    "action": current_action,
                    "observation": observation,
                })
                current_action = None

        return pairs

    def _format_pairs(self, pairs: List[Dict[str, str]]) -> str:
        """Format action-observation pairs for prompt.

        Args:
            pairs: List of action-observation dicts.

        Returns:
            Formatted string.
        """
        if not pairs:
            return "无"
        lines = []
        for i, p in enumerate(pairs):
            lines.append(f"Step {i+1}: Action={p['action']}, Observation={p['observation'][:100]}")
        return "\n".join(lines)

    def generate_updates(
        self,
        failure_analysis: Dict[str, Any],
        existing_skills: List[Skill],
    ) -> List[SkillUpdate]:
        """Generate skill updates based on failure analysis.

        Args:
            failure_analysis: Analysis result from analyze().
            existing_skills: Skills potentially related to the failure.

        Returns:
            List of SkillUpdate objects to apply.
        """
        updates = []
        for skill in existing_skills:
            if self._is_related_skill(skill, failure_analysis):
                update = self._create_update(skill, failure_analysis)
                if update:
                    updates.append(update)
        return updates

    def _is_related_skill(self, skill: Skill, analysis: Dict[str, Any]) -> bool:
        """Check if a skill is related to the failure analysis.

        Args:
            skill: Skill to check.
            analysis: Failure analysis result.

        Returns:
            True if skill is related.
        """
        # Simplified: consider all skills of the same task type as related
        return True

    def _create_update(
        self,
        skill: Skill,
        analysis: Dict[str, Any],
    ) -> Optional[SkillUpdate]:
        """Create a SkillUpdate based on failure analysis.

        Args:
            skill: Skill to update.
            analysis: Failure analysis result.

        Returns:
            SkillUpdate object, or None if no update needed.
        """
        reason = analysis.get("failure_reason", "")

        if reason == "missing_prerequisite":
            return SkillUpdate(
                skill_id=skill.skill_id,
                update_type="add_constraint",
                new_constraints=[analysis.get("failure_detail", "")],
                warning=f"注意：{analysis.get('lesson', '')}",
            )
        elif reason == "wrong_action":
            return SkillUpdate(
                skill_id=skill.skill_id,
                update_type="create_antipattern",
                antipattern={
                    "action": analysis.get("failure_action"),
                    "wrong_reason": analysis.get("failure_detail"),
                    "correct_approach": analysis.get("correct_approach"),
                },
            )
        elif reason == "wrong_order":
            return SkillUpdate(
                skill_id=skill.skill_id,
                update_type="add_failure_scenario",
                failure_scenario={
                    "reason": "wrong_order",
                    "detail": analysis.get("failure_detail"),
                    "correct_approach": analysis.get("correct_approach"),
                },
            )
        else:
            return SkillUpdate(
                skill_id=skill.skill_id,
                update_type="add_failure_scenario",
                failure_scenario={
                    "reason": reason,
                    "detail": analysis.get("failure_detail"),
                    "lesson": analysis.get("lesson"),
                },
            )
