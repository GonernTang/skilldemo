"""Skill retrieval with multiple search modes."""

import re
from typing import List, Optional

from memrl.providers.base import BaseEmbedder, BaseLLM
from memrl.skills.skill import Skill
from memrl.skills.store import SkillStore


class SkillRetriever:
    """Skill retriever supporting multiple retrieval modes."""

    def __init__(
        self,
        skill_store: SkillStore,
        llm: Optional[BaseLLM] = None,
        embedder: Optional[BaseEmbedder] = None,
    ):
        """Initialize the SkillRetriever.

        Args:
            skill_store: Skill storage backend.
            llm: LLM provider for LLM-based retrieval.
            embedder: Embedder for vector-based retrieval.
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
        """Retrieve relevant skills using the specified method.

        Args:
            query: Task description or search query.
            task_type: Task type to filter by.
            observation: Current observation for dynamic retrieval.
            k: Number of skills to retrieve.
            method: Retrieval method - "llm", "keyword", "vector", or "hybrid".

        Returns:
            List of retrieved Skill objects.
        """
        if method == "llm":
            return self._retrieve_with_llm(query, observation, k)
        elif method == "keyword":
            return self._retrieve_with_keyword(query, task_type, k)
        elif method == "vector":
            return self._retrieve_with_vector(query, k)
        elif method == "hybrid":
            return self._retrieve_hybrid(query, task_type, observation, k)
        else:
            return []

    def _retrieve_with_llm(
        self,
        query: Optional[str],
        observation: Optional[str],
        k: int,
    ) -> List[Skill]:
        """Retrieve skills using pure LLM reasoning.

        Args:
            query: Task description.
            observation: Current observation.
            k: Number of skills to retrieve.

        Returns:
            List of matched Skill objects.
        """
        if not self.llm:
            return []

        all_skills = self.skill_store.get_all_skills()
        if not all_skills:
            return []

        # Format skills for LLM
        skills_list = self._format_skills_for_llm(all_skills)

        prompt = f"""你是一个任务执行助手，擅长根据任务描述匹配并使用相关技能(Skill)。

## 可用技能列表
{skills_list}

## 任务
当前任务描述: {query or '无'}
当前观察: {observation or '无'}

## 你的任务
仔细阅读所有可用技能，判断哪些技能与当前任务相关。
输出格式:
```
相关技能: skill_id_1, skill_id_2, ...
```
如果没有相关技能:
```
相关技能: None
```
"""

        response = self.llm.generate([{"role": "user", "content": prompt}])
        matched_ids = self._parse_llm_response(response)

        # Return matched skills (up to k)
        matched_skills = [s for s in all_skills if s.skill_id in matched_ids]
        return matched_skills[:k]

    def _format_skills_for_llm(self, skills: List[Skill]) -> str:
        """Format skills list for LLM consumption.

        Args:
            skills: List of skills to format.

        Returns:
            Formatted string of skill metadata.
        """
        lines = []
        for s in skills:
            lines.append(f"""- skill_id: {s.skill_id}
  name: {s.name}
  description: {s.description}
  task_type: {s.task_type}
  trigger_keywords: {s.trigger_keywords}
  applicable_observations: {s.applicable_observations}""")
        return "\n".join(lines)

    def _parse_llm_response(self, response: str) -> List[str]:
        """Parse skill IDs from LLM response.

        Args:
            response: LLM response text.

        Returns:
            List of matched skill IDs.
        """
        match = re.search(r'相关技能:\s*(.+)', response)
        if match:
            ids_str = match.group(1).strip()
            if ids_str == "None":
                return []
            return [id.strip() for id in ids_str.split(",")]
        return []

    def _retrieve_with_keyword(
        self,
        query: Optional[str],
        task_type: Optional[str],
        k: int,
    ) -> List[Skill]:
        """Retrieve skills using keyword matching.

        Args:
            query: Search query.
            task_type: Task type filter.
            k: Number of skills to retrieve.

        Returns:
            List of matched Skill objects.
        """
        if task_type:
            candidates = self.skill_store.get_skills_by_type(task_type)
        else:
            candidates = self.skill_store.get_all_skills()

        if not query:
            return candidates[:k]

        # Score by keyword overlap
        query_words = set(query.lower().split())
        scored = []
        for skill in candidates:
            skill_keywords = set(k.lower() for k in skill.trigger_keywords)
            overlap = query_words & skill_keywords
            if overlap:
                score = len(overlap) / max(len(skill_keywords), 1)
                scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:k]]

    def _retrieve_with_vector(
        self,
        query: Optional[str],
        k: int,
    ) -> List[Skill]:
        """Retrieve skills using vector similarity.

        Args:
            query: Search query.
            k: Number of skills to retrieve.

        Returns:
            List of matched Skill objects.
        """
        if not self.embedder or not query:
            return []

        candidates = self.skill_store.get_all_skills()
        if not candidates:
            return []

        # Compute similarities
        query_emb = self.embedder.embed_single(query)
        scored = []
        for skill in candidates:
            skill_text = f"{skill.name} {skill.description}"
            skill_emb = self.embedder.embed_single(skill_text)
            sim = self._cosine_similarity(query_emb, skill_emb)
            scored.append((skill, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:k]]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Cosine similarity score.
        """
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _retrieve_hybrid(
        self,
        query: Optional[str],
        task_type: Optional[str],
        observation: Optional[str],
        k: int,
    ) -> List[Skill]:
        """Hybrid retrieval combining multiple methods.

        First uses keyword for quick filtering, then LLM for precise ranking.

        Args:
            query: Search query.
            task_type: Task type filter.
            observation: Current observation.
            k: Number of skills to retrieve.

        Returns:
            List of matched Skill objects.
        """
        # Step 1: Quick keyword filter to get candidates (top 20)
        candidates = self._retrieve_with_keyword(query, task_type, k=20)

        # Step 2: If we have LLM, use it for precise ranking
        if self.llm and candidates:
            # Format only candidates for LLM
            skills_list = self._format_skills_for_llm(candidates)

            prompt = f"""你是一个任务执行助手，擅长根据任务描述匹配并使用相关技能(Skill)。

## 可用技能列表（已根据关键词筛选）
{skills_list}

## 任务
当前任务描述: {query or '无'}
当前观察: {observation or '无'}

## 你的任务
仔细阅读所有可用技能，判断哪些技能与当前任务最相关。
输出格式:
```
相关技能: skill_id_1, skill_id_2, ...
```
如果没有相关技能:
```
相关技能: None
```
"""

            response = self.llm.generate([{"role": "user", "content": prompt}])
            matched_ids = self._parse_llm_response(response)

            if matched_ids:
                matched_skills = [s for s in candidates if s.skill_id in matched_ids]
                return matched_skills[:k]

        return candidates[:k]

    def retrieve_for_observation(
        self,
        observation: str,
        task_context: Optional[str] = None,
        k: int = 2,
    ) -> List[Skill]:
        """Retrieve skills applicable to the current observation.

        Used in ReAct loop for dynamic skill retrieval.

        Args:
            observation: Current environment observation.
            task_context: Optional task description context.
            k: Number of skills to retrieve.

        Returns:
            List of applicable Skill objects.
        """
        candidates = self.skill_store.get_all_skills()
        matched = []

        for skill in candidates:
            if self._observation_matches(observation, skill):
                score = self._compute_observation_score(observation, skill)
                matched.append((skill, score))

        matched.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in matched[:k]]

    def _observation_matches(self, observation: str, skill: Skill) -> bool:
        """Check if observation matches skill's applicable conditions.

        Args:
            observation: Current observation text.
            skill: Skill to check.

        Returns:
            True if observation matches skill conditions.
        """
        obs_lower = observation.lower()
        # Keyword matching
        for keyword in skill.trigger_keywords:
            if keyword.lower() in obs_lower:
                return True
        # Observation pattern matching
        for pattern in skill.applicable_observations:
            if pattern.lower() in obs_lower:
                return True
        return False

    def _compute_observation_score(self, observation: str, skill: Skill) -> float:
        """Compute relevance score between observation and skill.

        Args:
            observation: Current observation.
            skill: Skill to score.

        Returns:
            Relevance score.
        """
        obs_lower = observation.lower()
        score = 0.0

        # Count keyword matches
        for keyword in skill.trigger_keywords:
            if keyword.lower() in obs_lower:
                score += 1.0

        # Count observation pattern matches
        for pattern in skill.applicable_observations:
            if pattern.lower() in obs_lower:
                score += 2.0  # Higher weight for observation patterns

        return score
