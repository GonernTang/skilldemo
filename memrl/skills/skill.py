"""Skill data models for the MemRL skill layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SkillStep:
    """A single step in a skill's execution sequence.

    Attributes:
        action: The action to perform at this step.
        observation_pattern: The condition that triggers this action.
        reasoning: Explanation of why this action is appropriate.
    """

    action: str
    observation_pattern: str
    reasoning: str


@dataclass
class Skill:
    """Represents a reusable skill with execution steps and metadata.

    Attributes:
        skill_id: Unique identifier for the skill.
        name: Human-readable name of the skill.
        description: Detailed description of what the skill does.
        task_type: Category of tasks this skill applies to.
        trigger_keywords: Keywords used for retrieval indexing.
        applicable_observations: List of observation patterns this skill handles.
        steps: Ordered list of steps to execute the skill.
        skill_type: Either 'primitive' (atomic) or 'composite' (hierarchical).
        parent_skill_id: ID of parent skill if this is a sub-skill.
        success_rate: Historical success rate (0.0 to 1.0).
        usage_count: Number of times this skill has been used.
        last_used_at: ISO timestamp of last usage.
        created_at: ISO timestamp of creation.
        source_trajectory_id: ID of the trajectory this skill was learned from.
        failure_scenarios: Known failure modes and conditions.
        antipatterns: Patterns that indicate incorrect usage.
        constraints: Rules and limitations for using this skill.
        deprecated: Whether this skill should no longer be used.
    """

    skill_id: str
    name: str
    description: str
    task_type: str
    trigger_keywords: List[str]
    applicable_observations: List[str]
    steps: List[SkillStep]
    skill_type: str = "primitive"
    parent_skill_id: Optional[str] = None

    # Statistics
    success_rate: float = 1.0
    usage_count: int = 0
    last_used_at: Optional[str] = None
    created_at: str = ""
    source_trajectory_id: Optional[str] = None

    # Failure tracking
    failure_scenarios: List[Dict[str, Any]] = field(default_factory=list)
    antipatterns: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    deprecated: bool = False

    def __post_init__(self) -> None:
        """Set default created_at timestamp if empty."""
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the skill to a dictionary representation.

        Returns:
            Dictionary containing all skill fields.
        """
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "trigger_keywords": list(self.trigger_keywords),
            "applicable_observations": list(self.applicable_observations),
            "steps": [
                {
                    "action": step.action,
                    "observation_pattern": step.observation_pattern,
                    "reasoning": step.reasoning,
                }
                for step in self.steps
            ],
            "skill_type": self.skill_type,
            "parent_skill_id": self.parent_skill_id,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at,
            "created_at": self.created_at,
            "source_trajectory_id": self.source_trajectory_id,
            "failure_scenarios": list(self.failure_scenarios),
            "antipatterns": list(self.antipatterns),
            "constraints": list(self.constraints),
            "deprecated": self.deprecated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """Create a Skill instance from a dictionary.

        Args:
            data: Dictionary containing skill data.

        Returns:
            A new Skill instance.
        """
        steps = [
            SkillStep(
                action=step["action"],
                observation_pattern=step["observation_pattern"],
                reasoning=step["reasoning"],
            )
            for step in data.get("steps", [])
        ]
        return cls(
            skill_id=data["skill_id"],
            name=data["name"],
            description=data["description"],
            task_type=data["task_type"],
            trigger_keywords=list(data["trigger_keywords"]),
            applicable_observations=list(data["applicable_observations"]),
            steps=steps,
            skill_type=data.get("skill_type", "primitive"),
            parent_skill_id=data.get("parent_skill_id"),
            success_rate=data.get("success_rate", 1.0),
            usage_count=data.get("usage_count", 0),
            last_used_at=data.get("last_used_at"),
            created_at=data.get("created_at", ""),
            source_trajectory_id=data.get("source_trajectory_id"),
            failure_scenarios=list(data.get("failure_scenarios", [])),
            antipatterns=list(data.get("antipatterns", [])),
            constraints=list(data.get("constraints", [])),
            deprecated=data.get("deprecated", False),
        )

    def add_failure_scenario(self, scenario: Dict[str, Any]) -> None:
        """Record a new failure scenario for this skill.

        Args:
            scenario: Dictionary describing the failure condition and outcome.
        """
        self.failure_scenarios.append(scenario)

    def add_antipattern(self, pattern: Dict[str, Any]) -> None:
        """Record an antipattern (incorrect usage pattern) for this skill.

        Args:
            pattern: Dictionary describing the incorrect pattern and correction.
        """
        self.antipatterns.append(pattern)

    def add_constraint(self, constraint: str) -> None:
        """Add a usage constraint to this skill.

        Args:
            constraint: A string describing a limitation or requirement.
        """
        self.constraints.append(constraint)

    def update_stats(self, success: bool) -> None:
        """Update usage statistics after a skill execution.

        Args:
            success: Whether the skill execution was successful.
        """
        self.usage_count += 1
        self.last_used_at = datetime.utcnow().isoformat()

        # Update success rate using incremental average
        if self.usage_count == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            # Original rate is weighted by previous usage count
            self.success_rate = (self.success_rate * (self.usage_count - 1) + (1.0 if success else 0.0)) / self.usage_count


@dataclass
class SkillUpdate:
    """Represents an update operation to be applied to a skill.

    Attributes:
        skill_id: ID of the skill to update.
        update_type: Type of update to perform.
        new_constraints: Constraints to add to the skill.
        warning: Warning message associated with the update.
        failure_scenario: Failure scenario to record.
        antipattern: Antipattern to record.
        deprecated: Whether to mark the skill as deprecated.
    """

    skill_id: str
    update_type: str
    new_constraints: List[str] = field(default_factory=list)
    warning: str = ""
    failure_scenario: Optional[Dict[str, Any]] = None
    antipattern: Optional[Dict[str, Any]] = None
    deprecated: bool = False
