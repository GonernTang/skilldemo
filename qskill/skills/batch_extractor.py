"""Batch skill extraction from accumulated trajectories."""

import json
import time
import hashlib
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from qskill.providers.base import BaseLLM
from qskill.skills.prompts import (
    build_general_skill_prompt,
    build_task_specific_skill_prompt,
    build_common_mistakes_prompt,
)


class TrajectoryBuffer:
    """Buffer to store trajectories locally before batch extraction.

    Trajectories are persisted to disk and tracked by extraction status.
    Extracted trajectories remain on disk but won't be re-extracted.
    """

    def __init__(self, storage_dir: str = "trajectories"):
        """Initialize the trajectory buffer.

        Args:
            storage_dir: Directory to store trajectory files.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Track extracted trajectory IDs to avoid re-extraction
        self.extracted_ids_file = self.storage_dir / ".extracted_ids.json"
        self.extracted_ids: set = set()
        self._load_extracted_ids()

        # Buffer for pending (unextracted) trajectories
        self.buffer: List[Dict[str, Any]] = []
        self._load_existing()

    def _load_extracted_ids(self):
        """Load previously extracted trajectory IDs from disk."""
        if self.extracted_ids_file.exists():
            try:
                with open(self.extracted_ids_file, 'r') as f:
                    self.extracted_ids = set(json.load(f))
            except Exception:
                self.extracted_ids = set()

    def _save_extracted_ids(self):
        """Save extracted trajectory IDs to disk."""
        with open(self.extracted_ids_file, 'w') as f:
            json.dump(list(self.extracted_ids), f)

    def _load_existing(self):
        """Load existing unextracted trajectories from storage.

        Only loads trajectories that haven't been extracted yet.
        """
        for traj_file in sorted(self.storage_dir.glob("trajectory_*.json")):
            # Skip the extracted IDs tracking file
            if traj_file.name == ".extracted_ids.json":
                continue
            try:
                with open(traj_file, 'r') as f:
                    traj = json.load(f)
                # Only add if not already extracted
                if traj.get("traj_id") not in self.extracted_ids:
                    self.buffer.append(traj)
            except Exception:
                pass

    @property
    def count(self) -> int:
        """Return current buffer count (unextracted trajectories)."""
        return len(self.buffer)

    @property
    def pending_count(self) -> int:
        """Return number of pending (unextracted) trajectories."""
        return len(self.buffer)

    def add(
        self,
        trajectory: List[Dict[str, Any]],
        task_description: str,
        task_type: str,
        success: bool,
    ) -> int:
        """Add a trajectory to the buffer and save to disk.

        Args:
            trajectory: Execution trajectory.
            task_description: Description of the task.
            task_type: Type/category of the task.
            success: Whether the task succeeded.

        Returns:
            Current buffer count after adding.
        """
        traj_id = f"{int(time.time())}_{hashlib.md5(task_description.encode()).hexdigest()[:8]}"
        traj_data = {
            "traj_id": traj_id,
            "task_description": task_description,
            "task_type": task_type,
            "success": success,
            "trajectory": trajectory,
        }

        # Save to disk
        traj_path = self.storage_dir / f"trajectory_{traj_id}.json"
        with open(traj_path, 'w') as f:
            json.dump(traj_data, f, ensure_ascii=False, indent=2)

        # Add to memory buffer
        self.buffer.append(traj_data)
        return len(self.buffer)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all buffered trajectories (unextracted only)."""
        return self.buffer

    def mark_extracted(self, traj_ids: List[str]):
        """Mark trajectories as extracted and remove from buffer.

        Trajectories remain on disk but won't be included in future
        extractions.

        Args:
            traj_ids: List of trajectory IDs to mark as extracted.
        """
        self.extracted_ids.update(traj_ids)
        self._save_extracted_ids()
        # Remove extracted trajectories from buffer (files remain on disk)
        self.buffer = [t for t in self.buffer if t.get("traj_id") not in self.extracted_ids]

    def get_by_type(self, task_type: str) -> List[Dict[str, Any]]:
        """Get trajectories filtered by task type."""
        return [t for t in self.buffer if t.get("task_type") == task_type]

    def get_successful(self) -> List[Dict[str, Any]]:
        """Get all successful trajectories."""
        return [t for t in self.buffer if t.get("success")]

    def get_failed(self) -> List[Dict[str, Any]]:
        """Get all failed trajectories."""
        return [t for t in self.buffer if not t.get("success")]

    def clear(self):
        """Clear the buffer and delete saved files."""
        for traj_file in self.storage_dir.glob("trajectory_*.json"):
            traj_file.unlink()
        self.buffer.clear()


class BatchSkillExtractor:
    """Extract skills in batch from accumulated trajectories."""

    # Task type to category mapping
    TASK_TYPE_CATEGORIES = {
        "pick_and_place": "alfworld/pick_and_place",
        "look_at_obj_in_light": "alfworld/look_at_obj_in_light",
        "clean": "alfworld/clean",
        "heat": "alfworld/heat",
        "cool": "alfworld/cool",
        "examine": "alfworld/examine",
    }

    # Available categories
    CATEGORIES = [
        "general",
        "alfworld/pick_and_place",
        "alfworld/look_at_obj_in_light",
        "alfworld/clean",
        "alfworld/heat",
        "alfworld/cool",
        "alfworld/examine",
        "common_mistakes",
    ]

    def __init__(
        self,
        llm: BaseLLM,
        storage_dir: str = "skills",
        on_skills_extracted: Optional[callable] = None,
    ):
        """Initialize the batch skill extractor.

        Args:
            llm: LLM provider for skill extraction.
            storage_dir: Directory to save extracted skills.
            on_skills_extracted: Optional callback(skills_dict) called after
                batch extraction with the newly extracted skills dict.
                The dict has keys: general_skills, task_specific_skills, common_mistakes.
        """
        self.llm = llm
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_dir / "batch_skills_index.json"
        self.markdown_dir = self.storage_dir / "markdown"
        self._on_skills_extracted = on_skills_extracted
        self._init_index()

    def _init_index(self):
        """Initialize the skills index."""
        if not self.index_path.exists():
            self._save_index({
                "general_skills": [],
                "task_specific_skills": {},
                "common_mistakes": []
            })

    def _save_index(self, index: Dict[str, Any]):
        """Save skills index to disk."""
        with open(self.index_path, 'w') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _load_index(self) -> Dict[str, Any]:
        """Load skills index from disk."""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r') as f:
                    data = f.read()
                    if not data.strip():
                        # Empty file, return default
                        return {"general_skills": [], "task_specific_skills": {}, "common_mistakes": []}
                    return json.loads(data)
            except (json.JSONDecodeError, IOError):
                # Invalid JSON or read error, return default
                return {"general_skills": [], "task_specific_skills": {}, "common_mistakes": []}
        return {"general_skills": [], "task_specific_skills": {}, "common_mistakes": []}

    def _format_trajectory(self, traj: Dict[str, Any]) -> str:
        """Format a trajectory for the LLM prompt."""
        lines = []
        lines.append(f"[Trajectory ID: {traj['traj_id']}]")
        lines.append(f"Task: {traj['task_description'][:200]}...")
        lines.append(f"Task Type: {traj['task_type']}")
        lines.append(f"Result: {'SUCCESS' if traj['success'] else 'FAILED'}")
        lines.append("Steps:")
        for i, step in enumerate(traj['trajectory'][:20]):  # Limit to first 20 steps
            action = step.get('action', '')
            obs = step.get('observation', '')[:100]
            lines.append(f"  {i+1}. Action: {action} -> Obs: {obs}...")
        return "\n".join(lines)

    def _generate_skill_name(self, title: str) -> str:
        """Convert a title to a valid skill name (kebab-case)."""
        # Remove special characters, lowercase, replace spaces with hyphens
        name = re.sub(r'[^\w\s-]', '', title.lower())
        name = re.sub(r'[\s_]+', '-', name)
        name = re.sub(r'-+', '-', name)
        return name.strip('-')

    def _generate_general_skills(self, trajectories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate general skills from all trajectories."""
        success_patterns = []
        failure_patterns = []

        for traj in trajectories:
            formatted = self._format_trajectory(traj)
            if traj['success']:
                success_patterns.append(formatted)
            else:
                failure_patterns.append(formatted)

        success_text = "\n---\n".join(success_patterns[:15])  # Max 15 successful
        failure_text = "\n---\n".join(failure_patterns[:15]) if failure_patterns else "N/A"

        # Determine extraction range based on number of trajectories
        num_trajs = len(success_patterns) + len(failure_patterns)
        if num_trajs < 5:
            extract_min, extract_max = 1, 1
        elif num_trajs < 10:
            extract_min, extract_max = 1, 2
        else:
            extract_min, extract_max = 2, 3

        prompt = build_general_skill_prompt(
            success_text=success_text,
            failure_text=failure_text,
            num_success=len(success_patterns),
            num_failure=len(failure_patterns),
            extract_min=extract_min,
            extract_max=extract_max,
        )

        response = self.llm.generate([{"role": "user", "content": prompt}])

        try:
            skills = json.loads(response)
            for skill in skills:
                if "name" not in skill or not skill["name"]:
                    skill["name"] = self._generate_skill_name(skill.get("title", "unnamed"))
                skill["category"] = "general"
                skill["skill_value"] = 0.5  # Initial Q-value for new skills
                skill["usage_count"] = 0  # Initialize usage counter
            return skills
        except json.JSONDecodeError:
            return []

    def _generate_task_specific_skills(self, trajectories: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Generate task-specific skills organized by task type."""
        # Group by task type
        by_type: Dict[str, List[Dict[str, Any]]] = {tt: [] for tt in self.TASK_TYPE_CATEGORIES.keys()}

        for traj in trajectories:
            task_type = traj.get('task_type', '')
            # Match task type from full path like "pick_and_place/..."
            for tt in self.TASK_TYPE_CATEGORIES.keys():
                if tt in task_type:
                    by_type[tt].append(traj)
                    break

        result = {}
        for task_type, trajs in by_type.items():
            if not trajs:
                continue

            category = self.TASK_TYPE_CATEGORIES.get(task_type, "general")
            success_patterns = []
            failure_patterns = []
            for traj in trajs:
                formatted = self._format_trajectory(traj)
                if traj['success']:
                    success_patterns.append(formatted)
                else:
                    failure_patterns.append(formatted)

            success_text = "\n---\n".join(success_patterns[:8])
            failure_text = "\n---\n".join(failure_patterns[:8]) if failure_patterns else "N/A"

            # Determine extraction range based on number of trajectories
            num_trajs = len(success_patterns) + len(failure_patterns)
            if num_trajs < 5:
                extract_min, extract_max = 1, 1
            elif num_trajs < 10:
                extract_min, extract_max = 1, 2
            else:
                extract_min, extract_max = 2, 3

            prompt = build_task_specific_skill_prompt(
                task_type=task_type,
                category=category,
                task_description=task_type.replace('_', ' '),
                success_text=success_text,
                failure_text=failure_text,
                num_success=len(success_patterns),
                num_failure=len(failure_patterns),
                extract_min=extract_min,
                extract_max=extract_max,
            )

            response = self.llm.generate([{"role": "user", "content": prompt}])

            try:
                skills = json.loads(response)
                for skill in skills:
                    if "name" not in skill or not skill["name"]:
                        skill["name"] = self._generate_skill_name(skill.get("title", f"{task_type}-skill"))
                    skill["category"] = category
                    skill["task_type"] = task_type
                    skill["skill_value"] = 0.5  # Initial Q-value for new skills
                    skill["usage_count"] = 0  # Initialize usage counter
                result[task_type] = skills
            except json.JSONDecodeError:
                result[task_type] = []

        return result

    def _generate_common_mistakes(self, trajectories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate common mistakes from failed trajectories."""
        failed_trajs = [t for t in trajectories if not t['success']]
        if not failed_trajs:
            return []

        failure_data = []
        for traj in failed_trajs[:15]:  # Max 15 failures
            failure_data.append(self._format_trajectory(traj))

        failure_text = "\n---\n".join(failure_data)

        # Determine extraction range based on number of failure trajectories
        num_failures = len(failed_trajs)
        if num_failures < 3:
            extract_min, extract_max = 1, 1
        elif num_failures < 5:
            extract_min, extract_max = 1, 2
        else:
            extract_min, extract_max = 2, 3

        prompt = build_common_mistakes_prompt(
            failure_text=failure_text,
            num_failures=len(failed_trajs),
            extract_min=extract_min,
            extract_max=extract_max,
        )

        response = self.llm.generate([{"role": "user", "content": prompt}])

        try:
            mistakes = json.loads(response)
            for mistake in mistakes:
                if "name" not in mistake or not mistake["name"]:
                    mistake["name"] = self._generate_skill_name(mistake.get("description", "common-mistake"))
                mistake["category"] = "common_mistakes"
                mistake["skill_value"] = 0.5  # Initial Q-value for new skills
                mistake["usage_count"] = 0  # Initialize usage counter
            return mistakes
        except json.JSONDecodeError:
            return []

    def extract_batch(self, trajectories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract skills in batch from all trajectories.

        Args:
            trajectories: List of trajectory data.

        Returns:
            Dictionary with general_skills, task_specific_skills, and common_mistakes.
        """
        if not trajectories:
            return {"general_skills": [], "task_specific_skills": {}, "common_mistakes": []}

        print(f"Batch extracting skills from {len(trajectories)} trajectories...")

        # Generate all skill types
        general_skills = self._generate_general_skills(trajectories)
        print(f"Generated {len(general_skills)} general skills")

        task_specific_skills = self._generate_task_specific_skills(trajectories)
        total_specific = sum(len(v) for v in task_specific_skills.values())
        print(f"Generated {total_specific} task-specific skills")

        common_mistakes = self._generate_common_mistakes(trajectories)
        print(f"Generated {len(common_mistakes)} common mistakes")

        result = {
            "general_skills": general_skills,
            "task_specific_skills": task_specific_skills,
            "common_mistakes": common_mistakes,
        }

        # Save to index
        index = self._load_index()

        # Merge new skills (avoid duplicates by name)
        existing_names = {s["name"] for s in index.get("general_skills", [])}
        for skill in general_skills:
            if skill["name"] not in existing_names:
                index["general_skills"].append(skill)

        for task_type, skills in task_specific_skills.items():
            if task_type not in index["task_specific_skills"]:
                index["task_specific_skills"][task_type] = []
            existing_names = {s["name"] for s in index["task_specific_skills"][task_type]}
            for skill in skills:
                if skill["name"] not in existing_names:
                    index["task_specific_skills"][task_type].append(skill)

        existing_names = {m["name"] for m in index.get("common_mistakes", [])}
        for mistake in common_mistakes:
            if mistake["name"] not in existing_names:
                index["common_mistakes"].append(mistake)

        self._save_index(index)
        print(f"Saved skills to {self.storage_dir}")

        # Save skills as Markdown files
        self._save_skills_as_markdown(general_skills, "general")
        for task_type, skills in task_specific_skills.items():
            self._save_skills_as_markdown(skills, task_type)
        self._save_skills_as_markdown(common_mistakes, "common_mistakes")

        # Notify listener if callback is set
        if self._on_skills_extracted:
            self._on_skills_extracted(result)

        return result

    def _save_skill_as_markdown(self, skill: Dict[str, Any]) -> None:
        """Save a single skill as a Markdown file.

        Args:
            skill: Skill dictionary with name, description, content, category.
        """
        name = skill.get("name", "unnamed")
        description = skill.get("description", "")
        category = skill.get("category", "general")
        content = skill.get("content", "")

        # Convert escaped newlines to actual newlines
        content = content.replace("\\n", "\n")

        # Create directory: skills/markdown/{skill-name}/
        skill_dir = self.markdown_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Build Markdown with YAML frontmatter
        lines = [
            "---",
            f"name: {name}",
            f"description: {description}",
            f"category: {category}",
            "---",
            "",
            f"{content}",
            "",
        ]

        # Write to SKILL.md
        skill_path = skill_dir / "SKILL.md"
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _save_skills_as_markdown(self, skills: List[Dict[str, Any]], subdir: str) -> None:
        """Save a list of skills as Markdown files.

        Args:
            skills: List of skill dictionaries.
            subdir: Subdirectory under markdown/ (e.g., 'general', 'pick_and_place').
        """
        for skill in skills:
            # Add task_type to skill if not present (for organization)
            if "task_type" not in skill:
                skill["task_type"] = subdir
            self._save_skill_as_markdown(skill)
