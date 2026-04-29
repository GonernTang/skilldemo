"""Skill extractor for extracting skills from trajectories."""

from typing import Any, Dict, List, Optional, Tuple

from qskill.providers.base import BaseLLM
from qskill.skills.skill import Skill


class SkillConfig:
    """Configuration for skill extraction (legacy compatibility class)."""

    def __init__(
        self,
        llm: BaseLLM,
        storage_dir: str = "skills",
        retrieval_method: str = "llm",
        extract_threshold: float = 0.7,
        retrieve_k: int = 3,
        auto_extract: bool = True,
        auto_analyze_failure: bool = True,
        value_alpha: float = 0.5,
        value_lambda: float = 0.5,
        min_steps: int = 2,
        max_steps: int = 10,
    ):
        self.llm = llm
        self.storage_dir = storage_dir
        self.retrieval_method = retrieval_method
        self.extract_threshold = extract_threshold
        self.retrieve_k = retrieve_k
        self.auto_extract = auto_extract
        self.auto_analyze_failure = auto_analyze_failure
        self.value_alpha = value_alpha
        self.value_lambda = value_lambda
        self.min_steps = min_steps
        self.max_steps = max_steps


class SkillExtractor:
    """Extract skills from trajectories using LLM.

    This is a simplified implementation that delegates to BatchSkillExtractor
    for actual extraction logic.
    """

    def __init__(
        self,
        llm: BaseLLM,
        storage_dir: str = "skills",
        min_steps: int = 2,
        max_steps: int = 10,
    ):
        """Initialize the skill extractor.

        Args:
            llm: LLM provider for skill extraction.
            storage_dir: Directory for skill storage.
            min_steps: Minimum number of steps required for extraction.
            max_steps: Maximum number of steps to consider.
        """
        self.llm = llm
        self.storage_dir = storage_dir
        self.min_steps = min_steps
        self.max_steps = max_steps

    def extract(
        self,
        trajectory: List[Dict[str, Any]],
        task_description: str,
        task_type: str,
    ) -> Optional[Skill]:
        """Extract a skill from a trajectory.

        Note: This is a legacy interface - actual extraction happens in BatchSkillExtractor.

        Args:
            trajectory: Execution trajectory.
            task_description: Description of the task.
            task_type: Type/category of the task.

        Returns:
            Extracted Skill object, or None if extraction failed.
        """
        # This is a stub implementation - actual extraction in BatchSkillExtractor
        return None


class ExtractionTrigger:
    """Determine when to trigger skill extraction based on trajectory analysis.

    This is a simplified implementation for legacy compatibility.
    """

    def __init__(self, config: SkillConfig):
        """Initialize the extraction trigger.

        Args:
            config: SkillConfig instance with extraction settings.
        """
        self.config = config
        self.extractor = SkillExtractor(
            llm=config.llm,
            storage_dir=config.storage_dir,
            min_steps=config.min_steps,
            max_steps=config.max_steps,
        )

    def should_extract(
        self,
        task_type: str,
        trajectory: List[Dict[str, Any]],
        success: bool = True,
    ) -> Tuple[bool, str]:
        """Determine if skill extraction should be triggered.

        Args:
            task_type: Type/category of the task.
            trajectory: Execution trajectory to analyze.
            success: Whether the task succeeded.

        Returns:
            Tuple of (should_extract, action_type).
            action_type is "extract_new", "update_existing", or "".
        """
        if not self.config.auto_extract:
            return False, ""

        if not success:
            return False, ""

        if not self._has_enough_steps(trajectory):
            return False, ""

        return True, "extract_new"

    def _has_enough_steps(self, trajectory: List[Dict[str, Any]]) -> bool:
        """Check if trajectory has enough steps for extraction.

        Args:
            trajectory: Execution trajectory.

        Returns:
            True if trajectory has enough steps.
        """
        # Count assistant actions as steps
        step_count = sum(
            1 for msg in trajectory if msg.get("role") == "assistant"
        )
        return step_count >= self.config.min_steps
