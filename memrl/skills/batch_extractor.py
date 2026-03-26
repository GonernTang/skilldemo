"""Batch skill extraction from accumulated trajectories."""

import json
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from memrl.providers.base import BaseLLM
from memrl.skills.skill import Skill, SkillStep


class TrajectoryBuffer:
    """Buffer to store trajectories locally before batch extraction."""

    def __init__(self, storage_dir: str = "trajectories"):
        """Initialize the trajectory buffer.

        Args:
            storage_dir: Directory to store trajectory files.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.buffer: List[Dict[str, Any]] = []
        self._load_existing()

    def _load_existing(self):
        """Load existing trajectories from storage."""
        for traj_file in sorted(self.storage_dir.glob("trajectory_*.json")):
            try:
                with open(traj_file, 'r') as f:
                    self.buffer.append(json.load(f))
            except Exception:
                pass

    @property
    def count(self) -> int:
        """Return current buffer count."""
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
        """Get all buffered trajectories."""
        return self.buffer

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

    # Task type definitions
    TASK_TYPES = {
        "pick_and_place": "任务类型：拾取物体并放置到指定位置",
        "look_at_obj_in_light": "任务类型：用光源照射物体进行检查",
        "clean": "任务类型：清洁物体后放置",
        "heat": "任务类型：加热物体",
        "cool": "任务类型：冷却物体",
        "examine": "任务类型：用特定物体检查另一个物体",
    }

    def __init__(self, llm: BaseLLM, storage_dir: str = "skills"):
        """Initialize the batch skill extractor.

        Args:
            llm: LLM provider for skill extraction.
            storage_dir: Directory to save extracted skills.
        """
        self.llm = llm
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_dir / "batch_skills_index.json"
        self._init_index()

    def _init_index(self):
        """Initialize the skills index."""
        if not self.index_path.exists():
            self._save_index({"general_skills": [], "task_specific_skills": {}, "common_mistakes": []})

    def _save_index(self, index: Dict[str, Any]):
        """Save skills index to disk."""
        with open(self.index_path, 'w') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _load_index(self) -> Dict[str, Any]:
        """Load skills index from disk."""
        if self.index_path.exists():
            with open(self.index_path, 'r') as f:
                return json.load(f)
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

        prompt = f"""You are an expert at distilling agent behavior patterns into concise, actionable skills.

Analyze these successful and failed trajectories from an embodied AI agent operating in household environments (ALFWorld).

SUCCESSFUL TRAJECTORIES:
{success_text}

FAILED TRAJECTORIES:
{failure_text}

Generate 8-12 GENERAL SKILLS that apply across ALL task types. These should be:
1. **Concise** - Each skill should be 1-2 sentences max
2. **Actionable** - Clear what to do, not vague principles
3. **Transferable** - Apply to pick_and_place, heat, cool, clean, examine, look_at_obj_in_light tasks
4. **Failure-aware** - Derived from what went wrong in failures

Format as JSON array:
[
    {{
        "skill_id": "gen_001",
        "title": "Short title (3-5 words)",
        "principle": "The core actionable insight in 1-2 sentences",
        "when_to_apply": "Specific trigger condition"
    }}
]

Focus on:
- Navigation and exploration strategies
- Object manipulation principles
- State tracking and goal decomposition
- Error recovery patterns
- Container/furniture interaction rules

Return ONLY the JSON array, no other text."""

        response = self.llm.generate([{"role": "user", "content": prompt}])

        try:
            skills = json.loads(response)
            # Add skill_id if missing
            for i, skill in enumerate(skills):
                if "skill_id" not in skill:
                    skill["skill_id"] = f"gen_{i+1:03d}"
            return skills
        except json.JSONDecodeError:
            return []

    def _generate_task_specific_skills(self, trajectories: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Generate task-specific skills organized by task type."""
        # Group by task type
        by_type: Dict[str, List[Dict[str, Any]]] = {tt: [] for tt in self.TASK_TYPES.keys()}

        for traj in trajectories:
            task_type = traj.get('task_type', '')
            # Match task type from full path like "pick_and_place/..."
            for tt in self.TASK_TYPES.keys():
                if tt in task_type:
                    by_type[tt].append(traj)
                    break

        result = {}
        for task_type, trajs in by_type.items():
            if not trajs:
                continue

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

            prompt = f"""You are an expert at distilling agent behavior patterns into concise, actionable skills.

Task Type: {task_type.upper()}
Description: {self.TASK_TYPES.get(task_type, '')}

SUCCESSFUL TRAJECTORIES:
{success_text}

FAILED TRAJECTORIES:
{failure_text}

Generate 4-6 TASK-SPECIFIC SKILLS for {task_type} tasks. These should be:
1. **Concise** - 1-2 sentences max per skill
2. **Specific** - Apply specifically to {task_type} tasks
3. **Actionable** - Clear steps or decision rules
4. **Pattern-based** - Identify what makes success vs failure

Format as JSON array:
[
    {{
        "skill_id": "{task_type[:3]}_001",
        "title": "Short title (3-5 words)",
        "principle": "The core actionable insight",
        "when_to_apply": "Specific trigger condition"
    }}
]

Return ONLY the JSON array, no other text."""

            response = self.llm.generate([{"role": "user", "content": prompt}])

            try:
                skills = json.loads(response)
                for i, skill in enumerate(skills):
                    if "skill_id" not in skill:
                        skill["skill_id"] = f"{task_type[:3]}_{i+1:03d}"
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

        prompt = f"""You are an expert at analyzing agent failures and distilling them into avoidable mistakes.

Analyze these failure patterns from an embodied AI agent:

{failure_text}

Generate 8-12 COMMON MISTAKES to avoid. Format as JSON array:
[
    {{
        "mistake_id": "err_001",
        "description": "What the mistake is (1 sentence)",
        "why_it_happens": "Why agents make this mistake (1 sentence)",
        "how_to_avoid": "Concrete actionable fix (1-2 sentences)"
    }}
]

Focus on:
- Exploration failures (getting stuck, not finding objects)
- State management errors (forgetting what you're holding)
- Goal misunderstanding (wrong object, incomplete task)
- Inefficient action sequences

Return ONLY the JSON array, no other text."""

        response = self.llm.generate([{"role": "user", "content": prompt}])

        try:
            mistakes = json.loads(response)
            for i, mistake in enumerate(mistakes):
                if "mistake_id" not in mistake:
                    mistake["mistake_id"] = f"err_{i+1:03d}"
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

        # Merge new skills (avoid duplicates by skill_id)
        existing_ids = {s["skill_id"] for s in index.get("general_skills", [])}
        for skill in general_skills:
            if skill["skill_id"] not in existing_ids:
                index["general_skills"].append(skill)

        for task_type, skills in task_specific_skills.items():
            if task_type not in index["task_specific_skills"]:
                index["task_specific_skills"][task_type] = []
            existing_ids = {s["skill_id"] for s in index["task_specific_skills"][task_type]}
            for skill in skills:
                if skill["skill_id"] not in existing_ids:
                    index["task_specific_skills"][task_type].append(skill)

        existing_ids = {m["mistake_id"] for m in index.get("common_mistakes", [])}
        for mistake in common_mistakes:
            if mistake["mistake_id"] not in existing_ids:
                index["common_mistakes"].append(mistake)

        self._save_index(index)
        print(f"Saved skills to {self.storage_dir}")

        return result
