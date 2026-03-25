"""Skill layer integration helpers for runners."""

from typing import Any, Dict, List, Optional

from memrl.providers.base import BaseEmbedder, BaseLLM
from memrl.skills.extractor import SkillConfig
from memrl.skills.manager import SkillManager
from memrl.skills.skill import Skill


class SkillIntegrator:
    """Helper class for integrating skill layer into existing runners."""

    def __init__(
        self,
        config: SkillConfig,
        llm: BaseLLM,
        embedder: Optional[BaseEmbedder] = None,
    ):
        """Initialize the SkillIntegrator.

        Args:
            config: Skill configuration.
            llm: LLM provider.
            embedder: Optional embedder for vector retrieval.
        """
        self.config = config
        self.llm = llm
        self.embedder = embedder
        self.skill_manager: Optional[SkillManager] = None

    def initialize(self) -> None:
        """Initialize the skill manager if skill layer is enabled."""
        if self.config.enabled:
            self.skill_manager = SkillManager(
                config=self.config,
                llm=self.llm,
                embedder=self.embedder,
            )

    def retrieve_skills(
        self,
        task_description: str,
        task_type: str,
        observation: Optional[str] = None,
        k: Optional[int] = None,
    ) -> List[Skill]:
        """Retrieve relevant skills for a task.

        Args:
            task_description: Description of the task.
            task_type: Type/category of the task.
            observation: Current observation (for dynamic retrieval).
            k: Number of skills to retrieve (defaults to config.retrieve_k).

        Returns:
            List of relevant Skill objects.
        """
        if not self.skill_manager:
            return []
        return self.skill_manager.retrieve(
            task_description=task_description,
            task_type=task_type,
            observation=observation,
            k=k or self.config.retrieve_k,
        )

    def extract_and_save_skill(
        self,
        trajectory: List[Dict[str, Any]],
        task_description: str,
        task_type: str,
        success: bool = True,
    ) -> Optional[Skill]:
        """Extract and save a skill from a trajectory.

        Args:
            trajectory: Execution trajectory.
            task_description: Task description.
            task_type: Task type/category.
            success: Whether the trajectory was successful.

        Returns:
            Extracted Skill object, or None if extraction failed.
        """
        if not self.skill_manager:
            return None
        return self.skill_manager.extract_and_save(
            trajectory=trajectory,
            task_description=task_description,
            task_type=task_type,
            success=success,
        )

    def analyze_failure_and_update(
        self,
        failed_trajectory: List[Dict[str, Any]],
        task_description: str,
        task_type: str,
    ) -> None:
        """Analyze a failed trajectory and update relevant skills.

        Args:
            failed_trajectory: Failed execution trajectory.
            task_description: Task description.
            task_type: Task type/category.
        """
        if not self.skill_manager:
            return
        self.skill_manager.analyze_failure_and_update(
            failed_trajectory=failed_trajectory,
            task_description=task_description,
            task_type=task_type,
        )

    def format_skills_for_context(self, skills: List[Skill]) -> str:
        """Format skills for injection into agent context.

        Args:
            skills: List of skills to format.

        Returns:
            Formatted string for context injection.
        """
        if not skills:
            return ""

        lines = ["你可以使用以下相关技能:\n"]
        for s in skills:
            lines.append(f"## {s.name}")
            lines.append(f"描述: {s.description}")
            if s.applicable_observations:
                lines.append(f"适用观察: {s.applicable_observations}")
            if s.steps:
                lines.append(f"执行步骤: " + " → ".join([st.action for st in s.steps]))
            if s.constraints:
                lines.append(f"注意: {'; '.join(s.constraints)}")
            if s.antipatterns:
                lines.append(f"禁忌: {'; '.join([a.get('action', '') for a in s.antipatterns])}")
            lines.append("")
        return "\n".join(lines)

    def append_skills_to_messages(
        self,
        messages: List[Dict[str, str]],
        skills: List[Skill],
    ) -> List[Dict[str, str]]:
        """Append skills to message list as a system message.

        Args:
            messages: Existing message list.
            skills: Skills to append.

        Returns:
            Messages with skills appended.
        """
        if not skills:
            return messages

        skills_text = self.format_skills_for_context(skills)
        skill_context = {
            "role": "system",
            "content": f"你可以使用以下相关技能:\n{skills_text}"
        }
        return messages + [skill_context]


def load_skill_config_from_dict(config: Dict[str, Any], llm: BaseLLM) -> SkillConfig:
    """Create a SkillConfig from a dictionary configuration.

    Args:
        config: Dictionary with skill configuration.
        llm: LLM provider.

    Returns:
        SkillConfig object.
    """
    return SkillConfig(
        llm=llm,
        storage_dir=config.get("storage_dir", "skills"),
        retrieval_method=config.get("retrieval_method", "llm"),
        extract_threshold=config.get("extract_threshold", 0.7),
        retrieve_k=config.get("retrieve_k", 3),
        auto_extract=config.get("auto_extract", True),
        auto_analyze_failure=config.get("auto_analyze_failure", True),
    )


def create_skill_integrator(
    config_dict: Dict[str, Any],
    llm: BaseLLM,
    embedder: Optional[BaseEmbedder] = None,
) -> SkillIntegrator:
    """Create a SkillIntegrator from a full configuration dictionary.

    Args:
        config_dict: Full configuration dictionary.
        llm: LLM provider.
        embedder: Optional embedder.

    Returns:
        Configured SkillIntegrator, or None if skills disabled.
    """
    skill_config_dict = config_dict.get("skill", {})
    if not skill_config_dict.get("enabled", False):
        return None

    skill_config = load_skill_config_from_dict(skill_config_dict, llm)
    integrator = SkillIntegrator(
        config=skill_config,
        llm=llm,
        embedder=embedder,
    )
    integrator.initialize()
    return integrator
