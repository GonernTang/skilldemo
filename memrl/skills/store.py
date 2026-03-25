"""Skill storage management with JSON file persistence."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from memrl.skills.skill import Skill, SkillUpdate


class SkillStore:
    """Manages persistence of Skill objects using JSON files."""

    def __init__(self, storage_dir: str = "skills"):
        """Initialize the SkillStore.

        Args:
            storage_dir: Directory path for storing skill JSON files.
        """
        self.storage_dir = Path(storage_dir)
        self.index_path = self.storage_dir / "index.json"
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensure the storage directory exists."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, skill: Skill) -> str:
        """Save a Skill to a JSON file and update the index.

        Args:
            skill: The Skill object to save.

        Returns:
            The skill_id of the saved skill.
        """
        skill_path = self.storage_dir / f"{skill.skill_id}.json"
        with open(skill_path, "w", encoding="utf-8") as f:
            json.dump(skill.to_dict(), f, ensure_ascii=False, indent=2)
        self._update_index(skill)
        return skill.skill_id

    def load(self, skill_id: str) -> Optional[Skill]:
        """Load a Skill from its JSON file.

        Args:
            skill_id: The unique identifier of the skill to load.

        Returns:
            The loaded Skill object, or None if not found.
        """
        skill_path = self.storage_dir / f"{skill_id}.json"
        if not skill_path.exists():
            return None
        with open(skill_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Skill.from_dict(data)

    def delete(self, skill_id: str) -> bool:
        """Delete a Skill file and remove it from the index.

        Args:
            skill_id: The unique identifier of the skill to delete.

        Returns:
            True if deleted, False if skill didn't exist.
        """
        skill_path = self.storage_dir / f"{skill_id}.json"
        if skill_path.exists():
            skill_path.unlink()
            self._remove_from_index(skill_id)
            return True
        return False

    def get_all_skills(self) -> List[Skill]:
        """Load all skills from storage.

        Returns:
            List of all Skill objects.
        """
        index = self._load_index()
        skills = []
        for entry in index.get("skills", []):
            skill = self.load(entry["skill_id"])
            if skill is not None:
                skills.append(skill)
        return skills

    def get_skills_by_type(self, task_type: str) -> List[Skill]:
        """Get all skills matching a specific task type.

        Args:
            task_type: The task type to filter by (supports prefix matching).

        Returns:
            List of matching Skill objects.
        """
        index = self._load_index()
        skill_ids = [
            entry["skill_id"]
            for entry in index.get("skills", [])
            if entry["task_type"] == task_type or entry["task_type"].startswith(task_type)
        ]
        return [self.load(sid) for sid in skill_ids if self.load(sid) is not None]

    def _load_index(self) -> Dict[str, Any]:
        """Load the index file.

        Returns:
            The index dictionary, or an empty index structure if none exists.
        """
        if not self.index_path.exists():
            return {"skills": [], "total_count": 0}
        with open(self.index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _update_index(self, skill: Skill) -> None:
        """Update the index file with a skill entry.

        Args:
            skill: The skill to add or update in the index.
        """
        index = self._load_index()

        # Check if skill already exists in index
        for entry in index["skills"]:
            if entry["skill_id"] == skill.skill_id:
                entry.update({
                    "name": skill.name,
                    "task_type": skill.task_type,
                    "keywords": skill.trigger_keywords,
                })
                break
        else:
            # New entry
            index["skills"].append({
                "skill_id": skill.skill_id,
                "name": skill.name,
                "task_type": skill.task_type,
                "keywords": skill.trigger_keywords,
            })

        index["total_count"] = len(index["skills"])

        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _remove_from_index(self, skill_id: str) -> None:
        """Remove a skill from the index.

        Args:
            skill_id: The skill_id to remove.
        """
        index = self._load_index()
        index["skills"] = [
            entry for entry in index["skills"] if entry["skill_id"] != skill_id
        ]
        index["total_count"] = len(index["skills"])

        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def update_skill(self, skill_id: str, updates: List[SkillUpdate]) -> bool:
        """Apply a list of updates to a skill.

        Args:
            skill_id: The skill to update.
            updates: List of SkillUpdate objects to apply.

        Returns:
            True if update was successful, False if skill not found.
        """
        skill = self.load(skill_id)
        if not skill:
            return False

        for update in updates:
            if update.update_type == "add_constraint":
                skill.constraints.extend(update.new_constraints)
            elif update.update_type == "add_failure_scenario":
                if update.failure_scenario:
                    skill.failure_scenarios.append(update.failure_scenario)
            elif update.update_type == "create_antipattern":
                if update.antipattern:
                    skill.antipatterns.append(update.antipattern)
            elif update.update_type == "deprecate":
                skill.deprecated = True

        self.save(skill)
        return True
