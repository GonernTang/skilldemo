"""Batch skill integration with trajectory buffer and batch extraction."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from memrl.providers.base import BaseLLM, BaseEmbedder
from memrl.skills.batch_extractor import BatchSkillExtractor, TrajectoryBuffer


class BatchSkillIntegrator:
    """Integrates batch skill extraction into the agent workflow.

    This class manages:
    1. Trajectory buffering - stores trajectories locally
    2. Batch extraction triggering - triggers extraction when N trajectories reached
    3. Skill retrieval - retrieves relevant skills for tasks
    4. Skill storage - persists extracted skills in JSON format
    """

    def __init__(
        self,
        llm: BaseLLM,
        extract_interval: int = 10,
        trajectory_dir: str = "trajectories",
        skills_dir: str = "skills",
        retrieval_method: str = "llm",
    ):
        """Initialize the batch skill integrator.

        Args:
            llm: LLM provider for skill extraction.
            extract_interval: Number of trajectories to accumulate before extraction.
            trajectory_dir: Directory to store trajectories.
            skills_dir: Directory to store extracted skills.
            retrieval_method: Method for retrieval - "llm", "keyword", or "hybrid".
        """
        self.extract_interval = extract_interval
        self.llm = llm
        self.retrieval_method = retrieval_method

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

    def retrieve_skills(
        self,
        task_description: str,
        task_type: str,
        observation: Optional[str] = None,
        k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant skills for a task.

        Args:
            task_description: Description of the task.
            task_type: Type/category of the task.
            observation: Current observation (optional).
            k: Number of skills to retrieve.

        Returns:
            List of retrieved skill dictionaries.
        """
        all_skills = self.get_all_skills()
        if not all_skills:
            return []

        general_skills = all_skills.get("general_skills", [])
        task_specific_skills = all_skills.get("task_specific_skills", {}).get(task_type, [])

        # Combine general and task-specific skills
        all_available = general_skills + task_specific_skills
        if not all_available:
            return []

        if self.retrieval_method == "llm":
            retrieved = self._retrieve_with_llm(task_description, observation, all_available, k)
        elif self.retrieval_method == "keyword":
            retrieved = self._retrieve_with_keyword(task_description, all_available, k)
        else:
            # Hybrid or default
            retrieved = self._retrieve_with_keyword(task_description, all_available, k)

        return retrieved[:k]

    def _retrieve_with_llm(
        self,
        query: str,
        observation: Optional[str],
        skills: List[Dict[str, Any]],
        k: int,
    ) -> List[Dict[str, Any]]:
        """Retrieve skills using LLM."""
        if not self.llm:
            return skills[:k]

        skills_text = self._format_skills_for_llm(skills)

        prompt = f"""You are a task execution assistant, skilled at matching relevant skills to tasks.

## Available Skills
{skills_text}

## Current Task
Task Description: {query}
Current Observation: {observation or 'N/A'}

## Your Task
Read all available skills and determine which ones are relevant to the current task.
Output format:
```
Relevant Skills: skill_id_1, skill_id_2, ...
```
If no relevant skills:
```
Relevant Skills: None
```"""

        response = self.llm.generate([{"role": "user", "content": prompt}])
        matched_ids = self._parse_llm_response(response)

        if matched_ids:
            matched = [s for s in skills if s.get("skill_id") in matched_ids]
            return matched

        return skills[:k]

    def _retrieve_with_keyword(
        self,
        query: str,
        skills: List[Dict[str, Any]],
        k: int,
    ) -> List[Dict[str, Any]]:
        """Retrieve skills using keyword matching."""
        query_words = set(query.lower().split())
        scored = []

        for skill in skills:
            skill_keywords = set(" ".join(skill.get("trigger_keywords", [])).lower().split())
            overlap = query_words & skill_keywords
            if overlap:
                score = len(overlap) / max(len(skill_keywords), 1)
                scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:k]]

    def _format_skills_for_llm(self, skills: List[Dict[str, Any]]) -> str:
        """Format skills list for LLM consumption."""
        lines = []
        for s in skills:
            lines.append(f"""- skill_id: {s.get("skill_id", "unknown")}
  title: {s.get("title", s.get("name", ""))}
  principle: {s.get("principle", s.get("description", ""))}
  when_to_apply: {s.get("when_to_apply", "")}
  task_type: {s.get("task_type", "general")}""")
        return "\n".join(lines)

    def _parse_llm_response(self, response: str) -> List[str]:
        """Parse skill IDs from LLM response."""
        match = re.search(r'Relevant Skills:\s*(.+)', response)
        if match:
            ids_str = match.group(1).strip()
            if ids_str == "None":
                return []
            return [id.strip() for id in ids_str.split(",")]
        return []

    def format_skills_for_context(self, skills: List[Dict[str, Any]]) -> str:
        """Format retrieved skills for injection into agent context.

        Args:
            skills: List of skill dictionaries.

        Returns:
            Formatted string for context injection.
        """
        if not skills:
            return ""

        lines = ["## Available Skills\n"]
        for s in skills:
            lines.append(f"""### {s.get('title', s.get('skill_id', 'Unknown'))}
**When to apply:** {s.get('when_to_apply', 'N/A')}
**Principle:** {s.get('principle', s.get('description', 'N/A'))}
""")
        return "\n".join(lines)

    def reset(self):
        """Reset the buffer and extraction state."""
        self.trajectory_buffer.clear()
        self.last_extraction_count = 0
