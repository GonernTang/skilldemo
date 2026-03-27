"""Batch skill integration with trajectory buffer and batch extraction."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from memrl.providers.base import BaseLLM, BaseEmbedder
from memrl.skills.batch_extractor import BatchSkillExtractor, TrajectoryBuffer
from memrl.skills.prompts import build_skill_ranking_prompt


class BatchSkillIntegrator:
    """Integrates batch skill extraction into the agent workflow.

    This class manages:
    1. Trajectory buffering - stores trajectories locally
    2. Batch extraction triggering - triggers extraction when N trajectories reached
    3. Skill retrieval - retrieves relevant skills for tasks (template or embedding mode)
    4. Skill storage - persists extracted skills in JSON format
    """

    # Task type keywords for template-based detection
    TASK_TYPE_KEYWORDS = {
        "pick_and_place": ["pick", "place", "put", "move", "grab", "hold"],
        "look_at_obj_in_light": ["look", "examine", "inspect", "light", "check"],
        "clean": ["clean", "wash", "wipe", "scrub", "dry"],
        "heat": ["heat", "warm", "microwave", "temperature"],
        "cool": ["cool", "refrigerate", "freeze", "chill"],
        "examine": ["examine", "look", "check", "verify", "test"],
    }

    def __init__(
        self,
        llm: BaseLLM,
        embedder: Optional[BaseEmbedder] = None,
        extract_interval: int = 10,
        trajectory_dir: str = "trajectories",
        skills_dir: str = "skills",
        retrieval_method: str = "template",
    ):
        """Initialize the batch skill integrator.

        Args:
            llm: LLM provider for skill extraction.
            embedder: Embedder for embedding-based retrieval (optional).
            extract_interval: Number of trajectories to accumulate before extraction.
            trajectory_dir: Directory to store trajectories.
            skills_dir: Directory to store extracted skills.
            retrieval_method: Method for retrieval - "template", "embedding", or "hybrid".
        """
        self.extract_interval = extract_interval
        self.llm = llm
        self.embedder = embedder
        self.retrieval_method = retrieval_method

        # Initialize components
        self.trajectory_buffer = TrajectoryBuffer(storage_dir=trajectory_dir)
        self.batch_extractor = BatchSkillExtractor(
            llm=llm,
            storage_dir=skills_dir,
            on_skills_extracted=self._on_skills_extracted,
        )

        # Track if extraction was triggered this cycle
        self.last_extraction_count = 0

        # Embedding cache for skills (name -> embedding)
        self._embedding_cache: Dict[str, List[float]] = {}
        # Track cached skill names for cache invalidation
        self._cached_skill_names: set = set()
        # Track skill signatures (name|description) to detect modifications
        self._skill_signatures: Dict[str, str] = {}

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
        self.trajectory_buffer.add(
            trajectory=trajectory,
            task_description=task_description,
            task_type=task_type,
            success=success,
        )

        # Check if extraction threshold reached (use pending count, not total buffer)
        pending_count = self.trajectory_buffer.pending_count
        if pending_count >= self.extract_interval and pending_count > self.last_extraction_count:
            self.last_extraction_count = pending_count
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

        # Mark trajectories as extracted (not deleted - files remain on disk)
        traj_ids = [t["traj_id"] for t in trajectories]
        self.trajectory_buffer.mark_extracted(traj_ids)
        self.last_extraction_count = 0

        return result

    def get_all_skills(self) -> Dict[str, Any]:
        """Get all stored skills.

        Returns:
            Dictionary with all stored skills.
        """
        return self.batch_extractor._load_index()

    def _detect_task_type(self, task_description: str) -> List[str]:
        """Detect task types based on keywords in task description.

        Args:
            task_description: The task description text.

        Returns:
            List of detected task types.
        """
        task_lower = task_description.lower()
        detected = []

        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task_lower:
                    if task_type not in detected:
                        detected.append(task_type)
                    break

        return detected if detected else ["general"]

    def retrieve_skills(
        self,
        task_description: str,
        task_type: str,
        observation: Optional[str] = None,
        k: int = 6,
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
        task_specific_skills = all_skills.get("task_specific_skills", {})
        common_mistakes = all_skills.get("common_mistakes", [])

        if self.retrieval_method == "template":
            return self._retrieve_template(
                task_description, general_skills,
                task_specific_skills, common_mistakes, k
            )
        elif self.retrieval_method == "embedding":
            return self._retrieve_embedding(
                task_description, general_skills, task_specific_skills,
                common_mistakes, k
            )
        else:
            # Hybrid: use template for initial filter, then LLM ranking
            return self._retrieve_hybrid(
                task_description, task_type, observation, general_skills,
                task_specific_skills, common_mistakes, k
            )

    def _retrieve_template(
        self,
        task_description: str,
        general_skills: List[Dict[str, Any]],
        task_specific_skills: Dict[str, List[Dict[str, Any]]],
        common_mistakes: List[Dict[str, Any]],
        k: int,
    ) -> List[Dict[str, Any]]:
        """Template-based retrieval using keyword matching.

        Args:
            task_description: The task description.
            task_type: The detected task type.
            general_skills: List of general skills.
            task_specific_skills: Dict of task-specific skills by type.
            common_mistakes: List of common mistakes.
            k: Number of skills to retrieve.

        Returns:
            List of retrieved skills.
        """
        detected_types = self._detect_task_type(task_description)

        # Add general skills (top k//2)
        selected = general_skills[:k // 2]

        # Add task-specific skills for detected types
        remaining = k - len(selected)
        for task_type_key in detected_types:
            if remaining <= 0:
                break
            type_skills = task_specific_skills.get(task_type_key, [])
            selected.extend(type_skills[:remaining])
            remaining = k - len(selected)

        # Always add common mistakes (up to 2)
        if len(common_mistakes) > 0:
            selected.extend(common_mistakes[:2])

        return selected[:k]

    def _get_skill_signature(self, skill: Dict[str, Any]) -> str:
        """Get a signature string for a skill that detects modifications.

        The signature is based on name and description - if either changes,
        the skill is considered modified.
        """
        name = skill.get("name", "")
        desc = skill.get("description", "")
        return f"{name}|{desc}"

    def _sync_embedding_cache(self, all_skills: List[tuple]) -> None:
        """Synchronize embedding cache with current skill set.

        Handles three cases:
        1. New skills: compute and add embedding
        2. Deleted skills: remove embedding from cache
        3. Modified skills: recompute embedding

        Args:
            all_skills: List of (category, skill) tuples representing current skills.
        """
        if not self.embedder:
            return

        # Build current skill info: name -> signature
        current_skill_names: set = set()
        current_skill_sigs: Dict[str, str] = {}
        for cat, skill in all_skills:
            name = skill.get("name", "")
            if name:
                current_skill_names.add(name)
                current_skill_sigs[name] = self._get_skill_signature(skill)

        # Find deleted skills and remove from cache
        deleted_names = self._cached_skill_names - current_skill_names
        for name in deleted_names:
            if name in self._embedding_cache:
                del self._embedding_cache[name]
            if name in self._skill_signatures:
                del self._skill_signatures[name]

        # Find new or modified skills that need embedding recomputation
        skills_needing_embed: List[tuple] = []
        for cat, skill in all_skills:
            name = skill.get("name", "")
            if not name:
                continue
            sig = current_skill_sigs[name]
            cached_sig = self._skill_signatures.get(name, None)
            # Compute if: new skill OR signature changed
            if name not in self._embedding_cache or cached_sig != sig:
                skills_needing_embed.append((cat, skill))

        if not skills_needing_embed:
            # No changes, just update the cached names
            self._cached_skill_names = current_skill_names
            return

        # Batch compute embeddings for new/modified skills
        skill_descs_for_embed = []
        indices_to_update = []
        for i, (cat, skill) in enumerate(all_skills):
            name = skill.get("name", "")
            sig = current_skill_sigs.get(name, "")
            cached_sig = self._skill_signatures.get(name, None)
            if name and (name not in self._embedding_cache or cached_sig != sig):
                skill_descs_for_embed.append(
                    f"{skill.get('name', '')}: {skill.get('description', '')}"
                )
                indices_to_update.append((i, name, sig))

        if skill_descs_for_embed:
            new_embeddings = self.embedder.embed(skill_descs_for_embed)
            for (_, name, sig), emb in zip(indices_to_update, new_embeddings):
                self._embedding_cache[name] = emb
                self._skill_signatures[name] = sig

        # Update cached names
        self._cached_skill_names = current_skill_names

    def _on_skills_extracted(self, skills_dict: Dict[str, Any]) -> None:
        """Callback invoked by BatchSkillExtractor when new skills are extracted.

        Immediately updates embedding cache for newly extracted skills.

        Args:
            skills_dict: Dict with keys general_skills, task_specific_skills, common_mistakes.
        """
        if not self.embedder:
            return
        for skill in skills_dict.get("general_skills", []):
            self.update_skill_embedding(skill)
        for task_type, skills in skills_dict.get("task_specific_skills", {}).items():
            for skill in skills:
                self.update_skill_embedding(skill)
        for mistake in skills_dict.get("common_mistakes", []):
            self.update_skill_embedding(mistake)

    def _retrieve_embedding(
        self,
        task_description: str,
        general_skills: List[Dict[str, Any]],
        task_specific_skills: Dict[str, List[Dict[str, Any]]],
        common_mistakes: List[Dict[str, Any]],
        k: int,
    ) -> List[Dict[str, Any]]:
        """Embedding-based retrieval using cosine similarity.

        Args:
            task_description: The task description.
            general_skills: List of general skills.
            task_specific_skills: Dict of task-specific skills by type.
            common_mistakes: List of common mistakes.
            k: Number of skills to retrieve.

        Returns:
            List of retrieved skills sorted by relevance.
        """
        if not self.embedder:
            # Fallback to template if no embedder
            return self._retrieve_template(
                task_description, general_skills,
                task_specific_skills, common_mistakes, k
            )

        # Flatten all skills with their categories
        all_skills = []
        for skill in general_skills:
            all_skills.append(("general", skill))
        for task_type, skills in task_specific_skills.items():
            for skill in skills:
                all_skills.append((task_type, skill))
        for mistake in common_mistakes:
            all_skills.append(("common_mistakes", mistake))

        if not all_skills:
            return []

        # Sync cache: add/update/remove embeddings for skills
        self._sync_embedding_cache(all_skills)

        # Encode task description
        query_embedding = self.embedder.embed([task_description])

        # Use cached embeddings for skill descriptions
        skill_embeddings = []
        for cat, skill in all_skills:
            name = skill.get("name", "")
            if name and name in self._embedding_cache:
                skill_embeddings.append(self._embedding_cache[name])
            else:
                # Fallback: should not happen after sync, but handle gracefully
                skill_embeddings.append([0.0] * 1536)  # placeholder

        # Compute cosine similarities
        similarities = []
        for i, (cat, skill) in enumerate(all_skills):
            sim = self._cosine_similarity(query_embedding[0], skill_embeddings[i])
            similarities.append((cat, skill, sim))

        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[2], reverse=True)

        # Prioritize: general skills first, then by similarity
        result = []
        general_count = min(k // 2, len(general_skills))
        result.extend([s for _, s, _ in similarities[:general_count]])

        remaining = k - len(result)
        if remaining > 0:
            non_general = [s for _, s, _ in similarities[general_count:] if _ != "general"]
            result.extend(non_general[:remaining])

        # Add common mistakes if there's room
        if len(result) < k:
            for _, mistake, _ in similarities:
                if len(result) >= k:
                    break
                if mistake not in result:
                    result.append(mistake)

        return result[:k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _retrieve_hybrid(
        self,
        task_description: str,
        task_type: str,
        observation: Optional[str],
        general_skills: List[Dict[str, Any]],
        task_specific_skills: Dict[str, List[Dict[str, Any]]],
        common_mistakes: List[Dict[str, Any]],
        k: int,
    ) -> List[Dict[str, Any]]:
        """Hybrid retrieval: keyword pre-filter + LLM ranking.

        For large skill sets (>20 skills), uses a two-stage approach:
        1. Quick keyword matching to get top 20 candidates
        2. LLM ranking of candidates

        Args:
            task_description: The task description.
            task_type: The detected task type.
            observation: Current observation.
            general_skills: List of general skills.
            task_specific_skills: Dict of task-specific skills by type.
            common_mistakes: List of common mistakes.
            k: Number of skills to retrieve.

        Returns:
            List of retrieved skills.
        """
        # Flatten all skills
        all_available = []
        all_available.extend(general_skills)
        for skills in task_specific_skills.values():
            all_available.extend(skills)
        all_available.extend(common_mistakes)

        if not all_available:
            return []

        # If small skill set, use direct LLM ranking
        if len(all_available) <= 20:
            return self._rank_with_llm(task_description, observation, all_available, k)

        # Two-stage: pre-filter with keyword matching, then LLM ranking
        candidates = self._keyword_prefilter(task_description, task_type, all_available, top_n=20)
        return self._rank_with_llm(task_description, observation, candidates, k)

    def _keyword_prefilter(
        self,
        task_description: str,
        task_type: str,
        skills: List[Dict[str, Any]],
        top_n: int,
    ) -> List[Dict[str, Any]]:
        """Quick keyword-based pre-filtering.

        Args:
            task_description: The task description.
            task_type: The detected task type.
            skills: All available skills.
            top_n: Number of candidates to return.

        Returns:
            Pre-filtered candidates.
        """
        query_words = set(task_description.lower().split())

        scored = []
        for skill in skills:
            score = 0
            desc = skill.get("description", "").lower()
            name = skill.get("name", "").lower()
            content = skill.get("content", "").lower()

            # Score based on keyword overlap
            desc_words = set(desc.split())
            name_words = set(name.split())
            content_words = set(content.split())

            # Word overlap with description (highest weight)
            overlap_desc = query_words & desc_words
            score += len(overlap_desc) * 3

            # Word overlap with name
            overlap_name = query_words & name_words
            score += len(overlap_name) * 2

            # Word overlap with content (lowest weight)
            overlap_content = query_words & content_words
            score += len(overlap_content) * 1

            # Bonus for task type match
            if task_type and skill.get("task_type") == task_type:
                score += 5

            # Bonus for category match
            if task_type and skill.get("category") == task_type:
                score += 3

            if score > 0:
                scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:top_n]]

    def _rank_with_llm(
        self,
        query: str,
        observation: Optional[str],
        skills: List[Dict[str, Any]],
        k: int,
    ) -> List[Dict[str, Any]]:
        """Rank skills using LLM.

        Args:
            query: The task description.
            observation: Current observation.
            skills: Skills to rank.
            k: Number of skills to return.

        Returns:
            Top-ranked skills.
        """
        if not self.llm:
            return skills[:k]

        skills_text = self._format_skills_for_llm(skills)

        prompt = build_skill_ranking_prompt(
            skills_text=skills_text,
            query=query,
            observation=observation or "N/A",
        )

        response = self.llm.generate([{"role": "user", "content": prompt}])
        matched_names = self._parse_llm_response(response)

        if matched_names:
            # Preserve order from LLM response
            matched = []
            for name in matched_names:
                for skill in skills:
                    if skill.get("name") == name and skill not in matched:
                        matched.append(skill)
            return matched[:k]

        return skills[:k]

    def _format_skills_for_llm(self, skills: List[Dict[str, Any]]) -> str:
        """Format skills list for LLM consumption (lightweight format).

        Args:
            skills: List of skill dictionaries.

        Returns:
            Formatted string for LLM ranking.
        """
        lines = []
        for s in skills:
            lines.append(f"""- name: {s.get("name", "unknown")}
  description: {s.get("description", "")}
  category: {s.get("category", "general")}""")
        return "\n".join(lines)

    def _parse_llm_response(self, response: str) -> List[str]:
        """Parse skill names from LLM response.

        Args:
            response: LLM response text.

        Returns:
            List of skill names.
        """
        match = re.search(r'Relevant Skills:\s*(.+)', response)
        if match:
            names_str = match.group(1).strip()
            if names_str == "None":
                return []
            return [name.strip() for name in names_str.split(",")]
        return []

    def format_skills_for_context(self, skills: List[Dict[str, Any]]) -> str:
        """Format retrieved skills for injection into agent context.

        Follows MetaClaw's format:
        ## Active Skills

        ### skill-name
        _Use when..._

        ## Skill Title

        Content...


        Args:
            skills: List of skill dictionaries.

        Returns:
            Formatted string for context injection.
        """
        if not skills:
            return ""

        lines = ["## Active Skills\n"]

        for s in skills:
            name = s.get("name", "unknown")
            description = s.get("description", "")
            content = s.get("content", "")

            lines.append(f"### {name}")
            lines.append(f"_{description}_\n")
            lines.append(content)
            lines.append("")  # Empty line between skills

        return "\n".join(lines)

    def reset(self):
        """Reset the buffer and extraction state."""
        self.trajectory_buffer.clear()
        self.last_extraction_count = 0

    # ============== Public Embedding Cache Management ==============

    def invalidate_skill(self, name: str) -> None:
        """Immediately invalidate the embedding cache for a skill.

        Call this when a skill is deleted or renamed.

        Args:
            name: Name of the skill to invalidate.
        """
        if name in self._embedding_cache:
            del self._embedding_cache[name]
        if name in self._skill_signatures:
            del self._skill_signatures[name]
        if name in self._cached_skill_names:
            self._cached_skill_names.discard(name)

    def update_skill_embedding(self, skill: Dict[str, Any]) -> None:
        """Immediately compute and update embedding for a single skill.

        Call this when a skill is created or modified.

        Args:
            skill: Skill dictionary with 'name' and 'description' keys.
        """
        if not self.embedder:
            return
        name = skill.get("name", "")
        if not name:
            return
        description = f"{name}: {skill.get('description', '')}"
        embedding = self.embedder.embed([description])[0]
        self._embedding_cache[name] = embedding
        self._skill_signatures[name] = self._get_skill_signature(skill)
        self._cached_skill_names.add(name)

    def sync_embedding_cache(self) -> None:
        """Manually trigger full embedding cache synchronization.

        Re-reads all skills from storage and syncs the embedding cache.
        Call this after bulk modifications to skills.
        """
        all_skills_data = self.get_all_skills()
        all_skills = []
        for skill in all_skills_data.get("general_skills", []):
            all_skills.append(("general", skill))
        for task_type, skills in all_skills_data.get("task_specific_skills", {}).items():
            for skill in skills:
                all_skills.append((task_type, skill))
        for mistake in all_skills_data.get("common_mistakes", []):
            all_skills.append(("common_mistakes", mistake))
        self._sync_embedding_cache(all_skills)
