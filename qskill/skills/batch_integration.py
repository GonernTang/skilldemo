"""Batch skill integration with trajectory buffer and batch extraction."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from qskill.providers.base import BaseLLM, BaseEmbedder
from qskill.skills.batch_extractor import BatchSkillExtractor, TrajectoryBuffer
from qskill.skills.prompts import build_skill_ranking_prompt, build_task_summarization_prompt

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None


class BatchSkillIntegrator:
    """Integrates batch skill extraction into the agent workflow.

    This class manages:
    1. Trajectory buffering - stores trajectories locally
    2. Batch extraction triggering - triggers extraction when N trajectories reached
    3. Skill retrieval - retrieves relevant skills for tasks (template or embedding mode)
    4. Skill storage - persists extracted skills in JSON format
    """

    # Task type keywords for template-based detection
    # Format: for single-condition types, list of keywords (OR)
    # Format: for multi-condition types (AND), list of keyword groups
    # e.g. pick_and_place requires BOTH "pick/find" keyword AND "put" keyword
    TASK_TYPE_KEYWORDS = {
        # ALFWorld task types
        # pick_and_place: either "put" with destination OR "find/pick/grab" + "put"
        "pick_and_place": [["put ", "put them", "put it"], ["find ", "pick ", "grab ", "find two", "pick ", "grab "]],
        "look_at_obj_in_light": ["look at", "look quickly", "examine in", "inspect in"],
        "clean": ["clean ", "wash ", "wipe ", "scrub "],
        # heat: only the action keywords (cooling is done in fridge, but task is about heating)
        "heat": ["heat ", "warm "],
        # cool: only the action keywords
        "cool": ["cool ", "refrigerate", "chill "],
        "examine": ["examine the", "look at the", "check the", "verify the"],
        # BCB task types - library-based detection
        # BCB task_type format: "bcb/lib_name" where lib_name is from the libs field
        "bcb/subprocess": ["subprocess", "shell", "command", "run "],
        "bcb/os": ["os.path", "os.walk", "os.listdir", "os.rename", "os.remove"],
        "bcb/json": ["json", "json.dump", "json.load", "json.dumps", "json.loads"],
        "bcb/re": ["regex", "re.match", "re.search", "re.findall", "re.sub"],
        "bcb/datetime": ["datetime", "timedelta", "strftime", "strptime"],
        "bcb/collections": ["collections", "Counter", "defaultdict", "OrderedDict"],
        "bcb/itertools": ["itertools", "chain", "islice", "count"],
        "bcb/functools": ["functools", "lru_cache", "partial"],
        "bcb/random": ["random", "randint", "random.choice", "shuffle"],
        "bcb/math": ["math", "sqrt", "pow", "floor", "ceil"],
        "bcb/csv": ["csv", "csv.reader", "csv.writer", "DictReader", "DictWriter"],
        "bcb/zipfile": ["zipfile", "ZipFile", "zip"],
        "bcb/gzip": ["gzip", "gzip.open", "gzip.decompress"],
        "bcb/hashlib": ["hashlib", "md5", "sha1", "sha256"],
        "bcb/urllib": ["urllib", "urlopen", "urlretrieve", "quote"],
        "bcb/asyncio": ["asyncio", "async ", "await ", "gather"],
        "bcb/heapq": ["heapq", "heappush", "heappop", "heapify"],
        "bcb/pickle": ["pickle", "pickle.dump", "pickle.load", "dumps", "loads"],
        # HLE task types - category-based detection
        "hle/cs": ["Computer Science", "AI", "machine learning", "algorithm", "programming", "software", "neural", "deep learning", "NLP", "computer vision"],
        "hle/math": ["math", "equation", "calculus", "algebra", "geometry", "probability", "theorem", "proof", "number theory"],
        "hle/biology": ["biology", "bio", "cell", "DNA", "RNA", "protein", "organism", "genetics", "evolution", "ecology"],
        "hle/physics": ["physics", "force", "energy", "motion", "quantum", "thermodynamic", "electromagnetic", "mechanics", "relativity"],
        "hle/chemistry": ["chemistry", "chemical", "molecule", "reaction", "bond", "organic", "inorganic", "periodic", "catalyst", "compound"],
        "hle/engineering": ["engineering", "circuit", "signal", "control", "system", "mechanical", "electrical", "structural", "bridge", "robot"],
        "hle/humanities": ["humanities", "history", "philosophy", "literature", "psychology", "sociology", "economics", "political", "anthropology", "culture"],
        "hle/other": [],  # Default for uncategorized tasks
        # LLB task types - benchmark-based detection
        "llb/db": ["sql", "database", "query", "select", "insert", "update", "delete", "table", "column", "row", "db", "sqlite", "mysql", "postgresql"],
        "llb/os": ["shell", "bash", "command", "file", "directory", "path", "linux", "ubuntu", "cd", "ls", "mkdir", "rm", "cp", "mv", "cat", "grep", "awk", "sed"],
        "llb/kg": ["knowledge graph", "sparql", "rdf", "ontology", "entity", "triple", "link prediction", "kg", "graph query"],
    }

    def __init__(
        self,
        llm: BaseLLM,
        embedder: Optional[BaseEmbedder] = None,
        extract_interval: int = 10,
        trajectory_dir: str = "trajectories",
        skills_dir: str = "skills",
        benchmark: str = "markdown",
        retrieval_method: str = "template",
        value_alpha: float = 0.5,
        value_beta: float = 0.0,
        value_lambda: float = 0.5,
        retrieve_general: int = 1,
        retrieve_task_specific: int = 1,
        retrieve_common_mistakes: int = 1,
        summarize_task_description: bool = False,
        enable_culling: bool = False,
        max_skills: int = 50,
        cull_threshold: float = 0.3,
        cull_batch_size: int = 5,
        cull_min_usage: int = 3,
        enable_merging: bool = False,
        merge_similarity_threshold: float = 0.85,
        rrf_k: float = 60.0,
    ):
        """Initialize the batch skill integrator.

        Args:
            llm: LLM provider for skill extraction.
            embedder: Embedder for embedding-based retrieval (optional).
            extract_interval: Number of trajectories to accumulate before extraction.
            trajectory_dir: Directory to store trajectories.
            skills_dir: Directory to store extracted skills.
            benchmark: Benchmark name for organizing skills subdirectory (e.g., "alf", "bcb", "hle", "llb").
                Defaults to "markdown" for backward compatibility.
            retrieval_method: Method for retrieval - "template", "embedding", or "hybrid".
            value_alpha: Learning rate for skill value Q-learning update.
            value_beta: Weight for learning reward in LQRL (0 = standard Q-learning).
            value_lambda: Weight for skill value in hybrid retrieval score.
            retrieve_general: Number of general skills to retrieve.
            retrieve_task_specific: Number of task-specific skills to retrieve.
            retrieve_common_mistakes: Number of common mistakes to retrieve.
            summarize_task_description: If True, summarize task description before embedding.
            enable_culling: Enable automatic skill culling when count exceeds max_skills.
            max_skills: Maximum number of skills before culling is triggered.
            cull_threshold: Skill value threshold below which skills may be culled.
            cull_batch_size: Number of skills to cull at once.
            cull_min_usage: Minimum usage count before a skill can be culled.
            enable_merging: Enable automatic skill merging for similar skills.
            merge_similarity_threshold: Similarity threshold for merging.
            rrf_k: RRF (Reciprocal Rank Fusion) k parameter. Higher values
                give more weight to lower ranks. Default is 60.
        """
        self.extract_interval = extract_interval
        self.llm = llm
        self.embedder = embedder
        self.retrieval_method = retrieval_method
        self.value_alpha = value_alpha
        self.value_beta = value_beta
        self.value_lambda = value_lambda
        self.retrieve_general = retrieve_general
        self.retrieve_task_specific = retrieve_task_specific
        self.retrieve_common_mistakes = retrieve_common_mistakes
        self.summarize_task_description = summarize_task_description
        self.enable_culling = enable_culling
        self.max_skills = max_skills
        self.cull_threshold = cull_threshold
        self.cull_batch_size = cull_batch_size
        self.cull_min_usage = cull_min_usage
        self.enable_merging = enable_merging
        self.merge_similarity_threshold = merge_similarity_threshold
        self.rrf_k = rrf_k
        self.benchmark = benchmark

        # Initialize components
        self.trajectory_buffer = TrajectoryBuffer(storage_dir=trajectory_dir)
        self.batch_extractor = BatchSkillExtractor(
            llm=llm,
            storage_dir=skills_dir,
            benchmark=benchmark,
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

        # Persist embedding cache to disk (inside benchmark directory)
        self._skills_dir = Path(skills_dir) / benchmark
        self._embedding_cache_file = self._skills_dir / ".embedding_cache.json"
        self._load_embedding_cache()

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

    def extract_and_save_skill(
        self,
        trajectory: List[Dict[str, Any]],
        task_description: str,
        task_type: str,
        success: bool,
    ) -> Optional[Dict[str, Any]]:
        """Extract and save skill from a trajectory.

        This is an alias for add_trajectory to maintain compatibility.

        Args:
            trajectory: Execution trajectory.
            task_description: Description of the task.
            task_type: Type/category of the task.
            success: Whether the task succeeded.

        Returns:
            Extracted skills if extraction was triggered, None otherwise.
        """
        return self.add_trajectory(
            trajectory=trajectory,
            task_description=task_description,
            task_type=task_type,
            success=success,
        )

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

        # Check if culling is needed
        if self.enable_culling:
            self._cull_low_value_skills()

        return result

    def _cull_low_value_skills(self) -> None:
        """Cull low-value skills when skill count exceeds max_skills.

        Skills are evaluated based on skill_value, and those below cull_threshold
        with usage_count >= cull_min_usage are candidates for removal.
        """
        index = self.batch_extractor._load_index()

        # Count total skills
        total = len(index.get("general_skills", []))
        for task_skills in index.get("task_specific_skills", {}).values():
            total += len(task_skills)
        total += len(index.get("common_mistakes", []))

        if total <= self.max_skills:
            return  # No culling needed

        # Collect all skills with their metadata
        all_skills: List[tuple] = []
        for skill in index.get("general_skills", []):
            all_skills.append(("general", skill))
        for task_type, skills in index.get("task_specific_skills", {}).items():
            for skill in skills:
                all_skills.append((task_type, skill))
        for skill in index.get("common_mistakes", []):
            all_skills.append(("common_mistakes", skill))

        # Sort by skill_value ascending (lowest first)
        all_skills.sort(key=lambda x: x[1].get("skill_value", 0.0))

        # Identify skills to cull
        to_cull: List[tuple] = []
        remaining_slots = self.max_skills

        for cat_skill in all_skills:
            skill = cat_skill[1]
            skill_value = skill.get("skill_value", 0.0)
            usage_count = skill.get("usage_count", 0)

            # Skip if above threshold or below min usage
            if skill_value >= self.cull_threshold:
                break
            if usage_count < self.cull_min_usage:
                continue

            # Check if we have remaining slots
            if total - len(to_cull) <= remaining_slots:
                break

            to_cull.append(cat_skill)

        # Cull up to cull_batch_size skills
        to_cull = to_cull[: self.cull_batch_size]

        if not to_cull:
            return

        # Remove culled skills from index
        cull_names = {s[1].get("name") for s in to_cull}

        index["general_skills"] = [
            s for s in index.get("general_skills", []) if s.get("name") not in cull_names
        ]

        for task_type in list(index.get("task_specific_skills", {}).keys()):
            index["task_specific_skills"][task_type] = [
                s
                for s in index["task_specific_skills"][task_type]
                if s.get("name") not in cull_names
            ]

        index["common_mistakes"] = [
            s for s in index.get("common_mistakes", []) if s.get("name") not in cull_names
        ]

        # Save updated index
        self.batch_extractor._save_index(index)

        # Invalidate embedding cache for culled skills
        for name in cull_names:
            if name in self._embedding_cache:
                del self._embedding_cache[name]
            if name in self._skill_signatures:
                del self._skill_signatures[name]
        self._save_embedding_cache()

        print(f"Culled {len(to_cull)} low-value skills: {cull_names}")

    def get_all_skills(self) -> Dict[str, Any]:
        """Get all stored skills.

        Returns:
            Dictionary with all stored skills.
        """
        return self.batch_extractor._load_index()

    def _find_mergeable_skills(
        self, new_skills: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Find groups of skills that are similar enough to merge.

        Uses embedding similarity to find skills with high overlap,
        then returns groups for LLM-based merge decision.

        Args:
            new_skills: List of newly extracted skills to check against existing.

        Returns:
            List of skill groups (each group has 2+ skills) that may need merging.
        """
        if not self.enable_merging or not self.embedder or not new_skills:
            return []

        index = self.batch_extractor._load_index()

        # Collect all existing skills
        existing_skills: List[Dict[str, Any]] = []
        for skill in index.get("general_skills", []):
            existing_skills.append(skill)
        for task_skills in index.get("task_specific_skills", {}).values():
            existing_skills.extend(task_skills)
        for skill in index.get("common_mistakes", []):
            existing_skills.append(skill)

        if not existing_skills:
            return []

        # Sync embeddings for existing skills
        all_skills_with_cat = [("existing", s) for s in existing_skills]
        self._sync_embedding_cache(all_skills_with_cat)

        # Compute embeddings for new skills
        new_skill_texts = [
            f"{s.get('name', '')}: {s.get('description', '')}" for s in new_skills
        ]
        new_embeddings = self.embedder.embed(new_skill_texts)

        # Build existing embedding lookup
        name_to_embedding: Dict[str, List[float]] = {}
        for skill in existing_skills:
            name = skill.get("name", "")
            if name in self._embedding_cache:
                name_to_embedding[name] = self._embedding_cache[name]

        # Find similar pairs
        merge_groups: List[set] = []
        new_skill_names = [s.get("name", "") for s in new_skills]

        for i, new_skill in enumerate(new_skills):
            new_name = new_skill.get("name", "")
            if not new_name or new_name not in name_to_embedding:
                continue

            new_emb = new_embeddings[i]
            similar_existing = []

            for existing_skill in existing_skills:
                existing_name = existing_skill.get("name", "")
                if existing_name == new_name:
                    continue
                if existing_name not in name_to_embedding:
                    continue

                sim = self._cosine_similarity(new_emb, name_to_embedding[existing_name])
                if sim >= self.merge_similarity_threshold:
                    similar_existing.append(existing_name)

            if similar_existing:
                # Find or create a merge group
                found_group = False
                for group in merge_groups:
                    if any(sn in group for sn in similar_existing):
                        group.add(new_name)
                        group.update(similar_existing)
                        found_group = True
                        break
                if not found_group:
                    group = {new_name}
                    group.update(similar_existing)
                    merge_groups.append(group)

        # Convert sets to lists and ensure each group has 2+ skills
        result = [list(g) for g in merge_groups if len(g) >= 2]
        return result

    def _detect_task_type(self, task_description: str) -> List[str]:
        """Detect task types based on keywords in task description.

        Uses keyword matching for ALFWorld-style task descriptions.

        Args:
            task_description: The task description text.

        Returns:
            List of detected task types.
        """
        task_lower = task_description.lower()
        detected = []

        for task_type, keyword_groups in self.TASK_TYPE_KEYWORDS.items():
            if not keyword_groups:
                continue
            if isinstance(keyword_groups[0], list):
                # Multi-condition type (AND logic between groups)
                all_groups_match = True
                for group in keyword_groups:
                    group_match = any(kw in task_lower for kw in group)
                    if not group_match:
                        all_groups_match = False
                        break
                if all_groups_match and task_type not in detected:
                    detected.append(task_type)
            else:
                # Single-condition type (OR logic within list)
                for keyword in keyword_groups:
                    if keyword in task_lower:
                        if task_type not in detected:
                            detected.append(task_type)
                        break

        # Special case: "put X in Y" pattern without explicit pick/find/grab
        # This is a pick_and_place task even without the "pick" keyword
        if not any(t in detected for t in ["pick_and_place", "clean", "heat", "cool"]):
            # Check for "put" followed by object(s) and then "in/to/into" destination
            import re
            # Match: put + 1-2 words + in/to/into + destination
            put_pattern = re.search(r'put\s+(\w+\s+){1,2}(in|to|into)\s+', task_lower)
            if put_pattern:
                if "pick_and_place" not in detected:
                    detected.insert(0, "pick_and_place")

        return detected if detected else ["general"]

    def _normalize_task_type(self, task_type: str) -> str:
        """Extract the task category from a full task_type string.

        ALFWorld task_ids have format like 'train/cool' or 'valid_unseen/heat'.
        This method extracts just the category part ('cool', 'heat', etc.).

        For non-ALFWorld task_types, returns as-is.

        Args:
            task_type: Full task type string, e.g. 'train/cool' or just 'cool'.

        Returns:
            Normalized task category, e.g. 'cool'.
        """
        # Handle ALFWorld format: 'split/category' or 'split/subtype/category'
        # Examples: 'train/cool' -> 'cool', 'train/look_at_obj_in_light' -> 'look_at_obj_in_light'
        parts = task_type.split('/')
        if len(parts) >= 2:
            # Check if the last part looks like a known task type
            last_part = parts[-1]
            if last_part in self.TASK_TYPE_KEYWORDS:
                return last_part
            # Check second-to-last for cases like 'look_at_obj_in_light'
            if len(parts) >= 3 and parts[-2] in self.TASK_TYPE_KEYWORDS:
                return parts[-2]
        # Return as-is for non-ALFWorld formats
        return task_type

    def _summarize_task_description(self, task_description: str) -> str:
        """Summarize task description using LLM to extract core intent.

        This converts verbose ALFWorld task descriptions into concise action phrases
        that better match skill descriptions for embedding-based retrieval.

        Args:
            task_description: Original verbose task description.

        Returns:
            Summarized task description (concise action phrase).
        """
        if not self.llm:
            return task_description

        try:
            prompt = build_task_summarization_prompt(task_description)
            response = self.llm.generate([{"role": "user", "content": prompt}])

            # Parse the summarized task from response
            # Expected format: "Summarized Task: [concise action phrase]"
            if "Summarized Task:" in response:
                summarized = response.split("Summarized Task:")[1].strip()
                # Remove any quotes or extra text
                summarized = summarized.strip('"\'')
                return summarized
            return task_description
        except Exception:
            return task_description

    def retrieve_skills(
        self,
        task_description: str,
        task_type: str,
        observation: Optional[str] = None,
        k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant skills for a task.

        Args:
            task_description: Description of the task.
            task_type: Type/category of the task.
            observation: Current observation (optional).
            k: Number of skills to retrieve. If None, uses configured counts.

        Returns:
            List of retrieved skill dictionaries.
        """
        # Use configured counts if k not specified
        if k is None:
            k = self.retrieve_general + self.retrieve_task_specific + self.retrieve_common_mistakes

        all_skills = self.get_all_skills()
        if not all_skills:
            return []

        general_skills = all_skills.get("general_skills", [])
        task_specific_skills = all_skills.get("task_specific_skills", {})
        common_mistakes = all_skills.get("common_mistakes", [])

        if self.retrieval_method == "template":
            skills = self._retrieve_template(
                task_description, general_skills,
                task_specific_skills, common_mistakes, k, task_type
            )
        elif self.retrieval_method == "embedding":
            skills = self._retrieve_embedding(
                task_description, task_type, general_skills, task_specific_skills,
                common_mistakes, k
            )
        else:
            # Hybrid: use template for initial filter, then LLM ranking
            skills = self._retrieve_hybrid(
                task_description, task_type, observation, general_skills,
                task_specific_skills, common_mistakes, k
            )

        # Update usage count for retrieved skills
        if skills:
            skill_names = [s.get("name") for s in skills if s.get("name") is not None]
            self.increment_skills_usage_count(skill_names)

        return skills

    def _retrieve_template(
        self,
        task_description: str,
        general_skills: List[Dict[str, Any]],
        task_specific_skills: Dict[str, List[Dict[str, Any]]],
        common_mistakes: List[Dict[str, Any]],
        k: int,
        task_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Template-based retrieval using keyword matching.

        Args:
            task_description: The task description.
            general_skills: List of general skills.
            task_specific_skills: Dict of task-specific skills by type.
            common_mistakes: List of common mistakes.
            k: Number of skills to retrieve.
            task_type: Optional task type for benchmark-aware filtering.

        Returns:
            List of retrieved skills.
        """
        detected_types = self._detect_task_type(task_description)

        # Determine benchmark from task_type
        # BCB task_type format: "bcb/lib_name" or "bcb/lib_name/entry_point"
        # ALFWorld task_type format: "pick_and_place", "clean", etc.
        benchmark = None
        if task_type:
            if task_type.startswith("bcb/"):
                benchmark = "bcb"
            elif "/" not in task_type and task_type in self.TASK_TYPE_KEYWORDS:
                benchmark = "alfworld"

        # Add general skills (top k//2)
        # Filter general_skills by benchmark if they have benchmark metadata
        if benchmark:
            filtered_general = [
                s for s in general_skills
                if s.get("benchmark") is None or s.get("benchmark") == benchmark
            ]
        else:
            filtered_general = general_skills
        selected = filtered_general[:k // 2]

        # Add task-specific skills for detected types
        remaining = k - len(selected)
        for task_type_key in detected_types:
            if remaining <= 0:
                break
            # Only get task-specific skills that match the benchmark
            if benchmark == "bcb" and not task_type_key.startswith("bcb/"):
                continue
            if benchmark == "alfworld" and task_type_key.startswith("bcb/"):
                continue
            type_skills = task_specific_skills.get(task_type_key, [])
            # If no skills found and this is a BCB sub-type (e.g., bcb/json),
            # also check the generic bcb/task_func bucket
            if not type_skills and task_type_key.startswith("bcb/") and task_type_key != "bcb/task_func":
                type_skills = task_specific_skills.get("bcb/task_func", [])
            selected.extend(type_skills[:remaining])
            remaining = k - len(selected)

        # Add common mistakes (benchmark-aware filtering)
        # Only return common mistakes that match the current benchmark
        if len(common_mistakes) > 0:
            if benchmark:
                filtered_mistakes = [
                    m for m in common_mistakes
                    if m.get("benchmark") is None or m.get("benchmark") == benchmark
                ]
            else:
                filtered_mistakes = common_mistakes
            selected.extend(filtered_mistakes[:2])

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
        # Persist to disk
        self._save_embedding_cache()

    def _load_embedding_cache(self) -> None:
        """Load embedding cache from disk if exists."""
        if not self._embedding_cache_file.exists():
            return
        try:
            with open(self._embedding_cache_file, 'r') as f:
                data = json.load(f)
            self._embedding_cache = data.get('embeddings', {})
            self._skill_signatures = data.get('signatures', {})
            self._cached_skill_names = set(self._embedding_cache.keys())
        except Exception:
            self._embedding_cache = {}
            self._skill_signatures = {}
            self._cached_skill_names = set()

    def _save_embedding_cache(self) -> None:
        """Save embedding cache to disk."""
        data = {
            'embeddings': self._embedding_cache,
            'signatures': self._skill_signatures,
        }
        try:
            with open(self._embedding_cache_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass  # Ignore save errors

    def _on_skills_extracted(self, skills_dict: Dict[str, Any]) -> None:
        """Callback invoked by BatchSkillExtractor when new skills are extracted.

        Immediately updates embedding cache for newly extracted skills.
        If merging is enabled, also identifies and processes skill merges.

        Args:
            skills_dict: Dict with keys general_skills, task_specific_skills, common_mistakes.
        """
        if not self.embedder:
            return

        # Collect all newly extracted skills
        new_skills: List[Dict[str, Any]] = []
        for skill in skills_dict.get("general_skills", []):
            self.update_skill_embedding(skill)
            new_skills.append(skill)
        for task_type, skills in skills_dict.get("task_specific_skills", {}).items():
            for skill in skills:
                self.update_skill_embedding(skill)
                new_skills.append(skill)
        for mistake in skills_dict.get("common_mistakes", []):
            self.update_skill_embedding(mistake)
            new_skills.append(mistake)

        # Process merging if enabled
        if self.enable_merging and new_skills:
            merge_groups = self._find_mergeable_skills(new_skills)
            for group in merge_groups:
                self._merge_skills_by_name(group)

    def _merge_skills_by_name(self, skill_names: List[str]) -> None:
        """Merge multiple skills into one using LLM-based decision.

        This method is called when similar skills are detected. It gathers
        all skill details and asks the LLM to decide how to merge them.

        Args:
            skill_names: List of skill names to merge.
        """
        if len(skill_names) < 2:
            return

        # Load all skills by name
        index = self.batch_extractor._load_index()
        skills_to_merge: List[Dict[str, Any]] = []

        for name in skill_names:
            # Check general skills
            for skill in index.get("general_skills", []):
                if skill.get("name") == name:
                    skills_to_merge.append(skill)
                    break
            # Check task-specific skills
            if not any(s.get("name") == name for s in skills_to_merge):
                for task_skills in index.get("task_specific_skills", {}).values():
                    for skill in task_skills:
                        if skill.get("name") == name:
                            skills_to_merge.append(skill)
                            break
            # Check common mistakes
            if not any(s.get("name") == name for s in skills_to_merge):
                for skill in index.get("common_mistakes", []):
                    if skill.get("name") == name:
                        skills_to_merge.append(skill)
                        break

        if len(skills_to_merge) < 2:
            return

        # Ask LLM to merge
        merged = self._llm_merge_skills(skills_to_merge)
        if not merged:
            print(f"LLM merge failed for skills: {skill_names}")
            return

        # Remove merged skills from index
        merged_names = set(skill_names)
        for category_key in ["general_skills", "common_mistakes"]:
            index[category_key] = [
                s for s in index.get(category_key, []) if s.get("name") not in merged_names
            ]

        for task_type in list(index.get("task_specific_skills", {}).keys()):
            index["task_specific_skills"][task_type] = [
                s
                for s in index["task_specific_skills"][task_type]
                if s.get("name") not in merged_names
            ]

        # Add merged skill (if it has a new name, use it; otherwise use the first skill's name)
        new_skill_name = merged.get("name", skills_to_merge[0].get("name", "merged-skill"))
        merged["name"] = new_skill_name
        merged["skill_value"] = self._compute_merged_stat(skills_to_merge, "skill_value")
        merged["usage_count"] = sum(s.get("usage_count", 0) for s in skills_to_merge)
        merged["success_rate"] = self._compute_merged_stat(skills_to_merge, "success_rate")

        # Merge failure_scenarios, antipatterns, constraints, trigger_keywords
        merged["failure_scenarios"] = self._merge_lists(
            [s.get("failure_scenarios", []) for s in skills_to_merge]
        )
        merged["antipatterns"] = self._merge_lists([s.get("antipatterns", []) for s in skills_to_merge])
        merged["constraints"] = self._merge_lists([s.get("constraints", []) for s in skills_to_merge])
        merged["trigger_keywords"] = self._merge_lists(
            [s.get("trigger_keywords", []) for s in skills_to_merge]
        )

        # Determine category from first skill
        first_category = skills_to_merge[0].get("category", "general")
        if first_category in ["general", "common_mistakes"]:
            index[first_category].append(merged)
        else:
            task_type = first_category.replace("alfworld/", "")
            if task_type not in index["task_specific_skills"]:
                index["task_specific_skills"][task_type] = []
            index["task_specific_skills"][task_type].append(merged)

        # Save updated index
        self.batch_extractor._save_index(index)

        # Invalidate embeddings for old skills
        for name in merged_names:
            if name in self._embedding_cache:
                del self._embedding_cache[name]
        self._save_embedding_cache()

        print(f"Merged {len(skill_names)} skills into '{new_skill_name}'")

    def _llm_merge_skills(self, skills: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Use LLM to merge multiple similar skills.

        Args:
            skills: List of skill dictionaries to merge.

        Returns:
            Merged skill dictionary, or None if merge failed.
        """
        if not self.llm or len(skills) < 2:
            return None

        # Build prompt for merge decision
        skills_json = json.dumps(skills, indent=2, ensure_ascii=False)

        prompt = f"""你是一个技能融合专家。现在有多个高度相似的技能需要合并。

技能列表：
{skills_json}

请输出合并后的技能 JSON，要求：
1. 保留最关键的步骤，去除重复
2. 如果步骤顺序不同，分析哪种顺序更合理
3. 保持步骤的 observation_pattern 覆盖全面
4. 只输出 JSON，不要其他内容

输出格式：
{{
  "name": "合并后的技能名称",
  "description": "合并后的技能描述",
  "steps": [{{"action": "...", "observation_pattern": "...", "reasoning": "..."}}]
}}
"""

        try:
            response = self.llm.generate([{"role": "user", "content": prompt}])
            # Try to parse JSON from response
            # Handle cases where LLM adds markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code block syntax
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
                response = response.strip()

            merged = json.loads(response)
            return merged
        except (json.JSONDecodeError, Exception) as e:
            print(f"Failed to parse LLM merge response: {e}")
            return None

    def _compute_merged_stat(self, skills: List[Dict[str, Any]], stat_name: str) -> float:
        """Compute merged statistic from multiple skills.

        Uses weighted average based on usage_count.

        Args:
            skills: List of skills.
            stat_name: Name of the statistic to compute.

        Returns:
            Merged statistic value.
        """
        total_usage = 0
        weighted_sum = 0.0

        for skill in skills:
            usage = skill.get("usage_count", 0)
            value = skill.get(stat_name, 0.0)
            if usage > 0:
                weighted_sum += value * usage
                total_usage += usage

        return weighted_sum / total_usage if total_usage > 0 else 0.5

    def _merge_lists(self, lists: List[List[Any]]) -> List[Any]:
        """Merge multiple lists into one, removing duplicates.

        Args:
            lists: List of lists to merge.

        Returns:
            Merged list with unique items.
        """
        seen = set()
        result = []
        for lst in lists:
            for item in lst:
                # For dicts, use json.dumps as key; for primitives, use the item itself
                if isinstance(item, dict):
                    key = json.dumps(item, sort_keys=True)
                else:
                    key = str(item)
                if key not in seen:
                    seen.add(key)
                    result.append(item)
        return result

    def _retrieve_embedding(
        self,
        task_description: str,
        task_type: str,
        general_skills: List[Dict[str, Any]],
        task_specific_skills: Dict[str, List[Dict[str, Any]]],
        common_mistakes: List[Dict[str, Any]],
        k: int,
    ) -> List[Dict[str, Any]]:
        """Embedding-based retrieval using hybrid scoring (similarity + skill value).

        Skills are retrieved from each category based on configurable counts,
        then sorted by hybrid score within each category.

        Args:
            task_description: The task description.
            general_skills: List of general skills.
            task_specific_skills: Dict of task-specific skills by type.
            common_mistakes: List of common mistakes.
            k: Total number of skills to retrieve (used as fallback).

        Returns:
            List of retrieved skills sorted by relevance.
        """
        if not self.embedder:
            # Fallback to template if no embedder
            return self._retrieve_template(
                task_description, general_skills,
                task_specific_skills, common_mistakes, k, task_type
            )

        # Prepare all skills with their categories
        all_skills_with_cat = []
        for skill in general_skills:
            all_skills_with_cat.append(("general", skill))
        for specific_type, skills in task_specific_skills.items():
            for skill in skills:
                all_skills_with_cat.append((specific_type, skill))
        for mistake in common_mistakes:
            all_skills_with_cat.append(("common_mistakes", mistake))

        if not all_skills_with_cat:
            return []

        # Sync cache: add/update/remove embeddings for skills
        self._sync_embedding_cache(all_skills_with_cat)

        # Encode task description (optionally summarized first for better matching)
        if self.summarize_task_description:
            summarized_task = self._summarize_task_description(task_description)
        else:
            summarized_task = task_description
        query_embedding = self.embedder.embed([summarized_task])

        # Build embedding lookup dict: name -> embedding
        name_to_embedding = {}
        for cat, skill in all_skills_with_cat:
            name = skill.get("name", "")
            if name and name in self._embedding_cache:
                name_to_embedding[name] = self._embedding_cache[name]

        def compute_hybrid_score(skill: Dict[str, Any]) -> float:
            """Compute hybrid score for a skill."""
            name = skill.get("name", "")
            if name in name_to_embedding:
                sim = self._cosine_similarity(query_embedding[0], name_to_embedding[name])
            else:
                sim = 0.0
            q_value = skill.get("skill_value", 0.0)
            return (1 - self.value_lambda) * sim + self.value_lambda * q_value

        # Determine benchmark from task_type
        # BCB task_type format: "bcb/lib_name" or "bcb/lib_name/entry_point"
        # ALFWorld task_type format: "pick_and_place", "clean", etc.
        benchmark = None
        task_type_prefix = ""
        if task_type:
            if task_type.startswith("bcb/"):
                benchmark = "bcb"
                task_type_prefix = "bcb/"
            elif "/" not in task_type and task_type in self.TASK_TYPE_KEYWORDS:
                benchmark = "alfworld"

        # Normalize task_type from ALFWorld format (e.g., 'train/cool' -> 'cool')
        normalized_type = self._normalize_task_type(task_type)

        # Filter task_specific_skills to only include the normalized type if it exists
        # For BCB tasks, also filter by bcb/ prefix
        available_types = set(task_specific_skills.keys())
        valid_types = []

        if benchmark == "bcb":
            # BCB: only include types starting with "bcb/"
            valid_types = [t for t in available_types if t.startswith("bcb/")]
        elif benchmark == "alfworld":
            # ALFWorld: only include types NOT starting with "bcb/"
            valid_types = [t for t in available_types if not t.startswith("bcb/")]
            if normalized_type in available_types:
                valid_types = [normalized_type]
        else:
            # Unknown benchmark: use normalized type or detect from description
            if normalized_type in available_types:
                valid_types = [normalized_type]
            elif task_description:
                detected_from_desc = self._detect_task_type(task_description)
                valid_types = [t for t in detected_from_desc if t in available_types]

        # Benchmark-aware filtering for common_mistakes
        filtered_common_mistakes = []
        for mistake in common_mistakes:
            mistake_benchmark = mistake.get("benchmark")
            if mistake_benchmark is None or mistake_benchmark == benchmark:
                filtered_common_mistakes.append(mistake)
        common_mistakes = filtered_common_mistakes

        # Score and sort each category independently
        general_scored = [(compute_hybrid_score(s), s) for s in general_skills]
        general_scored.sort(key=lambda x: x[0], reverse=True)

        # For task_specific, only score skills from detected types (avoid cross-type contamination)
        task_specific_flat = []
        for specific_type, skills in task_specific_skills.items():
            if specific_type in valid_types:
                for skill in skills:
                    task_specific_flat.append(skill)
        task_specific_scored = [(compute_hybrid_score(s), s) for s in task_specific_flat]
        task_specific_scored.sort(key=lambda x: x[0], reverse=True)

        # Score common mistakes
        common_mistakes_scored = [(compute_hybrid_score(s), s) for s in common_mistakes]
        common_mistakes_scored.sort(key=lambda x: x[0], reverse=True)

        # Retrieve top N from each category based on hyperparameters
        n_general = min(self.retrieve_general, len(general_scored))
        n_task_specific = min(self.retrieve_task_specific, len(task_specific_scored))
        n_common_mistakes = min(self.retrieve_common_mistakes, len(common_mistakes_scored))

        # Combine results in order: general, task_specific, common_mistakes
        result = []
        result_names = set()

        for _, skill in general_scored[:n_general]:
            if skill.get("name") not in result_names:
                result.append(skill)
                result_names.add(skill.get("name"))

        for _, skill in task_specific_scored[:n_task_specific]:
            if skill.get("name") not in result_names:
                result.append(skill)
                result_names.add(skill.get("name"))

        for _, mistake in common_mistakes_scored[:n_common_mistakes]:
            if mistake.get("name") not in result_names:
                result.append(mistake)
                result_names.add(mistake.get("name"))

        return result

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
        """Hybrid retrieval: BM25 + Embedding + RRF fusion.

        Uses Reciprocal Rank Fusion to combine BM25 keyword matching
        and embedding-based semantic similarity.

        Args:
            task_description: The task description.
            task_type: The detected task type.
            observation: Current observation (unused, kept for API compatibility).
            general_skills: List of general skills.
            task_specific_skills: Dict of task-specific skills by type.
            common_mistakes: List of common mistakes.
            k: Number of skills to retrieve.

        Returns:
            List of retrieved skills sorted by RRF score.
        """
        # Flatten all skills
        all_available = []
        all_available.extend(general_skills)
        for skills in task_specific_skills.values():
            all_available.extend(skills)
        all_available.extend(common_mistakes)

        if not all_available:
            return []

        # RRF k parameter (configurable)
        rrf_k = getattr(self, 'rrf_k', 60)

        # Get BM25 scores (top-m)
        bm25_scores = self._retrieve_bm25(task_description, all_available, top_m=k * 2)

        # Get embedding scores (top-m)
        emb_scores = self._retrieve_embedding_scores(task_description, all_available, top_m=k * 2)

        # Compute RRF scores
        rrf_scores: Dict[int, float] = {}
        for i, (skill, bm25_score) in enumerate(bm25_scores):
            idx = id(skill)
            rank = i + 1  # 1-indexed
            if idx not in rrf_scores:
                rrf_scores[idx] = 0.0
            rrf_scores[idx] += 1.0 / (rrf_k + rank)

        for i, (skill, emb_score) in enumerate(emb_scores):
            idx = id(skill)
            rank = i + 1  # 1-indexed
            if idx not in rrf_scores:
                rrf_scores[idx] = 0.0
            rrf_scores[idx] += 1.0 / (rrf_k + rank)

        # Sort by RRF score and return top-k
        sorted_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        result = []
        seen_names = set()
        for idx in sorted_indices:
            # Find the skill with this id
            for skill in all_available:
                skill_name = skill.get('name', '')
                if id(skill) == idx and skill_name not in seen_names:
                    result.append(skill)
                    seen_names.add(skill_name)
                    break
            if len(result) >= k:
                break

        return result

    def _retrieve_bm25(
        self,
        query: str,
        skills: List[Dict[str, Any]],
        top_m: int,
    ) -> List[tuple]:
        """BM25-based retrieval.

        Args:
            query: The query string (task description).
            skills: List of skills to search.
            top_m: Number of top results to return.

        Returns:
            List of (skill, score) tuples sorted by BM25 score.
        """
        if not skills:
            return []

        # Prepare corpus: tokenize skill descriptions
        corpus = []
        for skill in skills:
            # Use name + description for BM25 indexing
            text = f"{skill.get('name', '')} {skill.get('description', '')}"
            # Simple tokenization: lowercase and split on whitespace/punctuation
            tokens = re.findall(r'\w+', text.lower())
            corpus.append(tokens)

        if not corpus or BM25Okapi is None:
            # Fallback: simple word overlap scoring
            return self._bm25_fallback(query, skills, top_m)

        # Build BM25 index
        bm25 = BM25Okapi(corpus)

        # Tokenize query
        query_tokens = re.findall(r'\w+', query.lower())

        # Get scores
        scores = bm25.get_scores(query_tokens)

        # Combine with skills and sort
        scored = [(skill, score) for skill, score in zip(skills, scores)]
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:top_m]

    def _bm25_fallback(
        self,
        query: str,
        skills: List[Dict[str, Any]],
        top_m: int,
    ) -> List[tuple]:
        """Fallback BM25-like scoring when rank_bm25 is unavailable.

        Uses simple TF-based scoring with length normalization.
        """
        query_words = set(re.findall(r'\w+', query.lower()))

        scored = []
        for skill in skills:
            text = f"{skill.get('name', '')} {skill.get('description', '')}"
            text_words = re.findall(r'\w+', text.lower())

            if not text_words:
                scored.append((skill, 0.0))
                continue

            # Count query word frequency in text
            text_word_count = {}
            for w in text_words:
                w_lower = w.lower()
                text_word_count[w_lower] = text_word_count.get(w_lower, 0) + 1

            # Compute score (similar to BM25 with k1=1.5, b=0.75)
            score = 0.0
            avg_len = len(text_words)
            for word in query_words:
                if word in text_word_count:
                    tf = text_word_count[word]
                    # Simplified BM25 formula
                    score += tf / (1.0 + 0.5 * (len(text_words) / max(avg_len, 1) - 1))

            scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_m]

    def _retrieve_embedding_scores(
        self,
        query: str,
        skills: List[Dict[str, Any]],
        top_m: int,
    ) -> List[tuple]:
        """Embedding-based retrieval with similarity scoring.

        Args:
            query: The query string (task description).
            skills: List of skills to search.
            top_m: Number of top results to return.

        Returns:
            List of (skill, score) tuples sorted by embedding similarity.
        """
        if not skills or not self.embedder:
            return [(skill, 0.0) for skill in skills[:top_m]]

        # Sync embedding cache first
        all_skills_with_cat = [(None, skill) for skill in skills]
        self._sync_embedding_cache(all_skills_with_cat)

        # Encode query
        query_embedding = self.embedder.embed([query])

        # Compute similarity for each skill
        scored = []
        for skill in skills:
            name = skill.get("name", "")
            if name in self._embedding_cache:
                emb = self._embedding_cache[name]
                sim = self._cosine_similarity(query_embedding[0], emb)
            else:
                sim = 0.0
            scored.append((skill, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_m]

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
        self._save_embedding_cache()

    def evaluate_failure_scenario(
        self,
        failure_scenario: Dict[str, Any],
        actual_error: str,
        task_context: str = "",
    ) -> float:
        """Evaluate the quality of a failure_scenario using LLM.

        This evaluates whether a failure_scenario is genuinely useful for
        avoiding similar failures, and returns an r_learning value.

        Args:
            failure_scenario: The failure scenario dict to evaluate.
            actual_error: The actual error that occurred during task execution.
            task_context: Optional context about the task for better evaluation.

        Returns:
            r_learning value between 0.0 and 0.5:
            - 0.0: failure_scenario is useless or misleading
            - 0.25: partially useful (describes error but advice imprecise)
            - 0.5: highly useful (accurately describes error with effective advice)
        """
        if not self.llm:
            return 0.0

        prompt = f"""You are a skill quality evaluator for AI agents.

## Task Error (what actually happened)
{actual_error}

## Extracted Failure Scenario
{failure_scenario}

## Task Context (if available)
{task_context if task_context else "No additional context provided."}

## Evaluation Criteria
Evaluate whether this failure_scenario is genuinely valuable:

1. **Relevance**: Does the failure_scenario accurately describe the error condition that caused the failure?
2. **Actionability**: Can the advice/solution help avoid similar failures?
3. **Non-redundancy**: Does the failure_scenario contain NEW information, not just obvious common sense?
4. **Correctness**: Is the suggested approach actually correct and effective?

## Important Notes
- A failure_scenario that merely restates obvious behavior (e.g., "don't use wrong parameters") is NOT useful
- A failure_scenario that misidentifies the cause of failure is HARMFUL (return 0.0)
- A failure_scenario that precisely pinpoints the error condition AND provides effective advice is HIGHLY USEFUL (return 0.5)

## Output Format
Return ONLY a number between 0.0 and 0.5 (use one decimal place if needed):
- 0.0 = useless or misleading
- 0.25 = partially useful
- 0.5 = highly useful

Do not include any explanation, just output the number."""

        try:
            response = self.llm.generate([{"role": "user", "content": prompt}])
            # Parse the response to extract a number
            response = response.strip()
            # Try to extract a number from the response
            import re
            numbers = re.findall(r'0?\.\d+', response)
            if numbers:
                score = float(numbers[0])
                # Clamp to [0.0, 0.5]
                return max(0.0, min(0.5, score))
            # If no number found, try integer
            if response in ['0', '0.0', '0.5', '0.25']:
                return float(response)
            # Default to 0.0 if parsing fails
            return 0.0
        except Exception:
            return 0.0

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
        self._save_embedding_cache()

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

    def update_skill_value_by_name(
        self,
        skill_name: str,
        success: bool,
        alpha: Optional[float] = None,
        r_learning: float = 0.0,
        beta: Optional[float] = None,
    ) -> bool:
        """Update skill value (Q-value) for a skill by name using Layered Q-Learning.

        LQRL formula: Q_new <- Q_old + alpha * [(1-beta)*r_task + beta*r_learning]

        Where:
        - r_task = 1.0 for success, 0.0 for failure
        - r_learning = content improvement reward (+0.5 improved, -0.5 degraded, 0 unchanged)
        - beta = weight balancing task reward vs learning reward (default: 0.3)

        When beta=0, this reduces to standard Q-learning.

        Args:
            skill_name: Name of the skill to update.
            success: Whether the skill execution was successful.
            alpha: Learning rate (uses instance default if not provided).
            r_learning: Learning reward for content improvement (default: 0.0).
            beta: Weight for learning reward channel (default: 0.3).

        Returns:
            True if skill was found and updated, False otherwise.
        """
        alpha = alpha if alpha is not None else self.value_alpha
        beta = beta if beta is not None else self.value_beta
        all_skills = self.get_all_skills()

        # Search in general_skills
        for skill in all_skills.get("general_skills", []):
            if skill.get("name") == skill_name:
                skill["skill_value"] = skill.get("skill_value", 0.0)
                r_task = 1.0 if success else 0.0
                r_total = (1 - beta) * r_task + beta * r_learning
                skill["skill_value"] = skill["skill_value"] + alpha * (r_total - skill["skill_value"])
                self._save_updated_index(all_skills)
                return True

        # Search in task_specific_skills
        for task_type, skills in all_skills.get("task_specific_skills", {}).items():
            for skill in skills:
                if skill.get("name") == skill_name:
                    skill["skill_value"] = skill.get("skill_value", 0.0)
                    r_task = 1.0 if success else 0.0
                    r_total = (1 - beta) * r_task + beta * r_learning
                    skill["skill_value"] = skill["skill_value"] + alpha * (r_total - skill["skill_value"])
                    self._save_updated_index(all_skills)
                    return True

        # Search in common_mistakes
        for skill in all_skills.get("common_mistakes", []):
            if skill.get("name") == skill_name:
                skill["skill_value"] = skill.get("skill_value", 0.0)
                r_task = 1.0 if success else 0.0
                r_total = (1 - beta) * r_task + beta * r_learning
                skill["skill_value"] = skill["skill_value"] + alpha * (r_total - skill["skill_value"])
                self._save_updated_index(all_skills)
                return True

        return False

    def increment_skill_usage_count(self, skill_name: str) -> bool:
        """Increment the usage count for a skill by name.

        Args:
            skill_name: Name of the skill to update.

        Returns:
            True if skill was found and updated, False otherwise.
        """
        all_skills = self.get_all_skills()

        # Search in general_skills
        for skill in all_skills.get("general_skills", []):
            if skill.get("name") == skill_name:
                skill["usage_count"] = skill.get("usage_count", 0) + 1
                self._save_updated_index(all_skills)
                return True

        # Search in task_specific_skills
        for task_type, skills in all_skills.get("task_specific_skills", {}).items():
            for skill in skills:
                if skill.get("name") == skill_name:
                    skill["usage_count"] = skill.get("usage_count", 0) + 1
                    self._save_updated_index(all_skills)
                    return True

        # Search in common_mistakes
        for skill in all_skills.get("common_mistakes", []):
            if skill.get("name") == skill_name:
                skill["usage_count"] = skill.get("usage_count", 0) + 1
                self._save_updated_index(all_skills)
                return True

        return False

    def increment_skills_usage_count(self, skill_names: List[str]) -> None:
        """Increment the usage count for multiple skills.

        Args:
            skill_names: List of skill names to update.
        """
        for name in skill_names:
            self.increment_skill_usage_count(name)

    def _save_updated_index(self, index: Dict[str, Any]) -> None:
        """Save updated skills index to disk.

        Args:
            index: Updated skills index dictionary.
        """
        index_path = self._skills_dir / "batch_skills_index.json"
        try:
            with open(index_path, 'w') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Ignore save errors
