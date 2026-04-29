"""Skill retrieval system."""

from typing import Any, List, Optional

from qskill.providers.base import BaseEmbedder, BaseLLM
from qskill.skills.skill import Skill
from qskill.skills.store import SkillStore


class SkillRetriever:
    """Retrieve skills based on query and task context.

    This is a simplified implementation that provides basic
    template-based and keyword-based retrieval.
    """

    def __init__(
        self,
        skill_store: SkillStore,
        llm: BaseLLM,
        embedder: Optional[BaseEmbedder] = None,
    ):
        """Initialize the skill retriever.

        Args:
            skill_store: SkillStore instance for loading skills.
            llm: LLM provider for LLM-based retrieval.
            embedder: Embedder for embedding-based retrieval.
        """
        self.skill_store = skill_store
        self.llm = llm
        self.embedder = embedder

    def retrieve(
        self,
        query: Optional[str] = None,
        task_type: Optional[str] = None,
        observation: Optional[str] = None,
        k: int = 3,
        method: str = "llm",
    ) -> List[Skill]:
        """Retrieve skills relevant to the current context.

        Args:
            query: Query string for retrieval.
            task_type: Type/category of the task.
            observation: Current observation (for dynamic retrieval).
            k: Number of skills to retrieve.
            method: Retrieval method ("llm", "keyword", "vector", "hybrid").

        Returns:
            List of relevant Skill objects.
        """
        all_skills = self.skill_store.get_all_skills()

        # Filter by task_type if specified
        if task_type:
            filtered = [s for s in all_skills if s.task_type.startswith(task_type)]
        else:
            filtered = all_skills

        # Sort by skill_value (Q-value) and return top-k
        filtered.sort(key=lambda s: s.skill_value, reverse=True)
        return filtered[:k]

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
        all_skills = self.skill_store.get_all_skills()
        applicable = []

        for skill in all_skills:
            if self._observation_matches(observation, skill):
                applicable.append(skill)

        # Sort by skill_value and return top-k
        applicable.sort(key=lambda s: s.skill_value, reverse=True)
        return applicable[:k]

    def _observation_matches(self, observation: str, skill: Skill) -> bool:
        """Check if an observation matches a skill's applicable observations.

        Args:
            observation: Current observation string.
            skill: Skill to check against.

        Returns:
            True if observation matches any of the skill's applicable observations.
        """
        observation_lower = observation.lower()
        for pattern in skill.applicable_observations:
            pattern_lower = pattern.lower()
            # Simple keyword matching
            if pattern_lower in observation_lower:
                return True
            # Also check if key words from pattern appear in observation
            pattern_words = set(pattern_lower.split())
            obs_words = set(observation_lower.split())
            if pattern_words and pattern_words.issubset(obs_words):
                return True
        return False
