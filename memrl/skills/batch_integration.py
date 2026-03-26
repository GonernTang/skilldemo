"""Batch skill integration with trajectory buffer and batch extraction."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from memrl.providers.base import BaseLLM, BaseEmbedder
from memrl.skills.batch_extractor import BatchSkillExtractor, TrajectoryBuffer


class BatchSkillIntegrator:
    """Integrates batch skill extraction into the agent workflow.

    This class manages:
    1. Trajectory buffering - stores trajectories locally
    2. Batch extraction triggering - triggers extraction when N trajectories reached
    3. Skill storage - persists extracted skills
    """

    def __init__(
        self,
        llm: BaseLLM,
        extract_interval: int = 10,
        trajectory_dir: str = "trajectories",
        skills_dir: str = "skills",
    ):
        """Initialize the batch skill integrator.

        Args:
            llm: LLM provider for skill extraction.
            extract_interval: Number of trajectories to accumulate before extraction.
            trajectory_dir: Directory to store trajectories.
            skills_dir: Directory to store extracted skills.
        """
        self.extract_interval = extract_interval
        self.llm = llm

        # Initialize components
        self.trajectory_buffer = TrajectoryBuffer(storage_dir=trajectory_dir)
        self.batch_extractor = BatchSkillExtractor(llm=llm, storage_dir=skills_dir)

        # Track if extraction was triggered this cycle
        self.last_extraction_count = 0

    @property
    def pending_count(self) -> int:
        """Number of pending trajectories in buffer."""
        return self.trajectory_buffer.count

    def add_trajectory(
        self,
        trajectory: List[Dict[str, Any]],
        task_description: str,
        task_type: str,
        success: bool,
    ) -> Optional[Dict[str, Any]]:
        """Add a trajectory to the buffer and trigger extraction if threshold reached.

        Args:
            trajectory: Execution trajectory.
            task_description: Description of the task.
            task_type: Type/category of the task.
            success: Whether the task succeeded.

        Returns:
            Extracted skills if extraction was triggered, None otherwise.
        """
        # Add to buffer
        count = self.trajectory_buffer.add(
            trajectory=trajectory,
            task_description=task_description,
            task_type=task_type,
            success=success,
        )

        # Check if extraction threshold reached
        if count >= self.extract_interval and count > self.last_extraction_count:
            self.last_extraction_count = count
            return self.trigger_batch_extraction()

        return None

    def trigger_batch_extraction(self) -> Dict[str, Any]:
        """Manually trigger batch skill extraction.

        Returns:
            Extracted skills dictionary.
        """
        trajectories = self.trajectory_buffer.get_all()
        if not trajectories:
            return {"general_skills": [], "task_specific_skills": {}, "common_mistakes": []}

        # Extract skills in batch
        result = self.batch_extractor.extract_batch(trajectories)

        # Clear buffer after extraction
        self.trajectory_buffer.clear()
        self.last_extraction_count = 0

        return result

    def get_all_skills(self) -> Dict[str, Any]:
        """Get all stored skills.

        Returns:
            Dictionary with all stored skills.
        """
        return self.batch_extractor._load_index()

    def reset(self):
        """Reset the buffer and extraction state."""
        self.trajectory_buffer.clear()
        self.last_extraction_count = 0
