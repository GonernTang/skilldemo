"""Skill layer integration for runners - unified batch system."""

from typing import Any, Dict, Optional

from memrl.providers.base import BaseEmbedder, BaseLLM
from memrl.skills.batch_integration import BatchSkillIntegrator


def create_skill_integrator(
    config_dict: Dict[str, Any],
    llm: BaseLLM,
    embedder: Optional[BaseEmbedder] = None,
) -> Optional[BatchSkillIntegrator]:
    """Create a BatchSkillIntegrator from a full configuration dictionary.

    Args:
        config_dict: Full configuration dictionary.
        llm: LLM provider.
        embedder: Optional embedder for embedding-based retrieval.

    Returns:
        Configured BatchSkillIntegrator, or None if skills disabled.
    """
    skill_config = config_dict.get("skill", {})
    if not skill_config.get("enabled", False):
        return None

    extract_interval = skill_config.get("extract_interval", 10)
    retrieval_method = skill_config.get("retrieval_method", "template")
    storage_dir = skill_config.get("storage_dir", "skills")

    return BatchSkillIntegrator(
        llm=llm,
        embedder=embedder,
        extract_interval=extract_interval,
        trajectory_dir="trajectories",
        skills_dir=storage_dir,
        retrieval_method=retrieval_method,
    )
