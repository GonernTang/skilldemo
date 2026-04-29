"""Skill storage management."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from qskill.skills.skill import Skill


class SkillStore:
    """Manage skill storage in JSON format.

    This is a simplified implementation that stores skills as individual
    JSON files in a directory structure.
    """

    def __init__(self, storage_dir: str = "skills"):
        """Initialize the skill store.

        Args:
            storage_dir: Directory to store skill JSON files.
        """
        self.storage_dir = Path(storage_dir)
        self.general_dir = self.storage_dir / "general"
        self.task_dir = self.storage_dir / "task_specific"
        self.mistakes_dir = self.storage_dir / "common_mistakes"

        # Create directories if they don't exist
        self.general_dir.mkdir(parents=True, exist_ok=True)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.mistakes_dir.mkdir(parents=True, exist_ok=True)

        # Index file to track all skills
        self.index_file = self.storage_dir / "index.json"
        self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """Load the skill index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"general_skills": [], "task_specific_skills": {}, "common_mistakes": []}

    def _save_index(self, index: Dict[str, Any]) -> None:
        """Save the skill index to disk."""
        with open(self.index_file, 'w') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def save(self, skill: Skill) -> str:
        """Save a skill to storage.

        Args:
            skill: Skill object to save.

        Returns:
            Skill ID (name) that was saved.
        """
        # Determine category based on task_type
        if skill.task_type == "general" or skill.task_type.startswith("common_mistake"):
            save_dir = self.mistakes_dir if "mistake" in skill.task_type else self.general_dir
        else:
            save_dir = self.task_dir / skill.task_type
            save_dir.mkdir(parents=True, exist_ok=True)

        # Save skill to file
        skill_file = save_dir / f"{skill.name}.json"
        with open(skill_file, 'w') as f:
            json.dump(skill.to_dict(), f, ensure_ascii=False, indent=2)

        # Update index
        index = self._load_index()
        if skill.task_type == "general":
            if skill.name not in index["general_skills"]:
                index["general_skills"].append(skill.name)
        elif "mistake" in skill.task_type:
            if skill.name not in index["common_mistakes"]:
                index["common_mistakes"].append(skill.name)
        else:
            if skill.task_type not in index["task_specific_skills"]:
                index["task_specific_skills"][skill.task_type] = []
            if skill.name not in index["task_specific_skills"][skill.task_type]:
                index["task_specific_skills"][skill.task_type].append(skill.name)
        self._save_index(index)

        return skill.name

    def load(self, name: str) -> Optional[Skill]:
        """Load a skill by name.

        Args:
            name: Name of the skill to load.

        Returns:
            Skill object, or None if not found.
        """
        # Search in all directories
        for skill_file in self.storage_dir.rglob(f"{name}.json"):
            try:
                with open(skill_file, 'r') as f:
                    data = json.load(f)
                return Skill.from_dict(data)
            except Exception:
                pass
        return None

    def get_all_skills(self) -> List[Skill]:
        """Get all stored skills.

        Returns:
            List of all Skill objects.
        """
        skills = []
        for skill_file in self.storage_dir.rglob("*.json"):
            if skill_file.name == "index.json":
                continue
            try:
                with open(skill_file, 'r') as f:
                    data = json.load(f)
                skills.append(Skill.from_dict(data))
            except Exception:
                pass
        return skills

    def get_skills_by_type(self, task_type: str) -> List[Skill]:
        """Get all skills of a specific type.

        Args:
            task_type: Task type to filter by.

        Returns:
            List of matching Skill objects.
        """
        return [s for s in self.get_all_skills() if s.task_type == task_type]

    def update_skill(self, name: str, updates: List[Any]) -> bool:
        """Apply updates to a skill.

        Args:
            name: Name of skill to update.
            updates: List of updates to apply.

        Returns:
            True if update was successful.
        """
        skill = self.load(name)
        if not skill:
            return False

        for update in updates:
            if hasattr(update, 'new_constraints') and update.new_constraints:
                for constraint in update.new_constraints:
                    skill.add_constraint(constraint)
            if hasattr(update, 'failure_scenario') and update.failure_scenario:
                skill.add_failure_scenario(update.failure_scenario)
            if hasattr(update, 'antipattern') and update.antipattern:
                skill.add_antipattern(update.antipattern)
            if hasattr(update, 'deprecated'):
                skill.deprecated = update.deprecated

        self.save(skill)
        return True
