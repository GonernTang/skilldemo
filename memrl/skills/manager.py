"""Skill manager integrating storage, retrieval, and extraction."""

from typing import Any, Dict, List, Optional

from memrl.providers.base import BaseEmbedder, BaseLLM
from memrl.skills.analyzer import FailureAnalyzer
from memrl.skills.extractor import SkillConfig, SkillExtractor
from memrl.skills.retriever import SkillRetriever
from memrl.skills.skill import Skill, SkillUpdate
from memrl.skills.store import SkillStore


class SkillManager:
    """Core skill manager integrating extraction, storage, and retrieval."""

    def __init__(
        self,
        config: SkillConfig,
        llm: BaseLLM,
        embedder: Optional[BaseEmbedder] = None,
    ):
        """Initialize the SkillManager.

        Args:
            config: Skill configuration.
            llm: LLM provider for extraction and LLM-based retrieval.
            embedder: Embedder for vector-based retrieval.
        """
        self.config = config
        self.store = SkillStore(storage_dir=config.storage_dir)
        self.extractor = SkillExtractor(llm=llm)
        self.retriever = SkillRetriever(
            skill_store=self.store,
            llm=llm,
            embedder=embedder,
        )
        self.failure_analyzer = FailureAnalyzer(llm=llm)

    # === Retrieval ===

    def retrieve(
        self,
        task_description: Optional[str] = None,
        task_type: Optional[str] = None,
        observation: Optional[str] = None,
        k: int = 3,
    ) -> List[Skill]:
        """Retrieve skills relevant to the current context.

        Args:
            task_description: Description of the task.
            task_type: Type/category of the task.
            observation: Current observation (for dynamic retrieval).
            k: Number of skills to retrieve.

        Returns:
            List of relevant Skill objects.
        """
        return self.retriever.retrieve(
            query=task_description,
            task_type=task_type,
            observation=observation,
            k=k,
            method=self.config.retrieval_method,
        )

    def retrieve_for_observation(
        self,
        observation: str,
        task_context: Optional[str] = None,
        k: int = 2,
    ) -> List[Skill]:
        """Retrieve skills applicable to current observation.

        Used in ReAct loop for dynamic skill retrieval.

        Args:
            observation: Current environment observation.
            task_context: Optional task description context.
            k: Number of skills to retrieve.

        Returns:
            List of applicable Skill objects.
        """
        return self.retriever.retrieve_for_observation(
            observation=observation,
            task_context=task_context,
            k=k,
        )

    # === Extraction ===

    def extract_and_save(
        self,
        trajectory: List[Dict[str, Any]],
        task_description: str,
        task_type: str,
        success: bool = True,
    ) -> Optional[Skill]:
        """Extract and save a skill from a successful trajectory.

        Args:
            trajectory: Execution trajectory.
            task_description: Task description.
            task_type: Task type/category.
            success: Whether the trajectory was successful.

        Returns:
            Extracted Skill object, or None if extraction failed.
        """
        if not success:
            return None

        skill = self.extractor.extract(
            trajectory=trajectory,
            task_description=task_description,
            task_type=task_type,
        )

        if skill:
            self.store.save(skill)

        return skill

    # === Statistics ===

    def update_skill_stats(self, skill_id: str, success: bool) -> None:
        """Update usage statistics for a skill.

        Args:
            skill_id: ID of the skill to update.
            success: Whether the skill usage was successful.
        """
        skill = self.store.load(skill_id)
        if skill:
            skill.update_stats(success)
            self.store.save(skill)

    # === Skill Access ===

    def load_skill(self, skill_id: str) -> Optional[Skill]:
        """Load a single skill by ID.

        Args:
            skill_id: Unique skill identifier.

        Returns:
            Skill object, or None if not found.
        """
        return self.store.load(skill_id)

    def get_all_skills(self) -> List[Skill]:
        """Get all stored skills.

        Returns:
            List of all Skill objects.
        """
        return self.store.get_all_skills()

    def get_skills_by_type(self, task_type: str) -> List[Skill]:
        """Get all skills of a specific type.

        Args:
            task_type: Task type to filter by.

        Returns:
            List of matching Skill objects.
        """
        return self.store.get_skills_by_type(task_type)

    def get_applicable_skills(
        self,
        observation: str,
        task_type: Optional[str] = None,
    ) -> List[Skill]:
        """Get skills applicable to current observation.

        Args:
            observation: Current observation.
            task_type: Optional task type filter.

        Returns:
            List of applicable Skill objects.
        """
        candidates = self.store.get_all_skills()
        applicable = []

        for skill in candidates:
            if task_type and not skill.task_type.startswith(task_type):
                continue
            if self.retriever._observation_matches(observation, skill):
                applicable.append(skill)

        return applicable

    # === Failure Analysis ===

    def analyze_failure_and_update(
        self,
        failed_trajectory: List[Dict[str, Any]],
        task_description: str,
        task_type: str,
        skill_ids: Optional[List[str]] = None,
    ) -> List[SkillUpdate]:
        """Analyze a failed trajectory and update relevant skills.

        Args:
            failed_trajectory: Failed execution trajectory.
            task_description: Task description.
            task_type: Task type/category.
            skill_ids: Optional list of specific skill IDs to update. If None,
                       all skills of the same task_type will be updated (legacy behavior).

        Returns:
            List of SkillUpdate objects that were applied.
        """
        # Step 1: LLM analyze failure
        analysis = self.failure_analyzer.analyze(
            failed_trajectory=failed_trajectory,
            task_description=task_description,
            task_type=task_type,
        )

        if not analysis:
            return []

        # Step 2: Get skills to update
        if skill_ids:
            # Precise mode: only update the specified skills
            related_skills = [self.store.load(sid) for sid in skill_ids]
            related_skills = [s for s in related_skills if s is not None]
        else:
            # Legacy mode: update all skills of the same task_type
            related_skills = self.store.get_skills_by_type(task_type)

        # Step 3: Generate updates
        updates = self.failure_analyzer.generate_updates(analysis, related_skills)

        # Step 4: Apply updates
        for update in updates:
            self.store.update_skill(update.skill_id, [update])

        return updates

    # === Skill Updates ===

    def update_skill(
        self,
        skill_id: str,
        updates: List[SkillUpdate],
    ) -> bool:
        """Apply updates to a skill.

        Args:
            skill_id: ID of skill to update.
            updates: List of updates to apply.

        Returns:
            True if update was successful.
        """
        return self.store.update_skill(skill_id, updates)

    def deprecate_skill(self, skill_id: str) -> bool:
        """Mark a skill as deprecated.

        Args:
            skill_id: ID of skill to deprecate.

        Returns:
            True if deprecation was successful.
        """
        skill = self.store.load(skill_id)
        if not skill:
            return False
        skill.deprecated = True
        self.store.save(skill)
        return True
