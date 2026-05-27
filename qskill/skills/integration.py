"""Skill layer integration for runners - unified batch system."""

from typing import Any, Dict, Optional

from qskill.providers.base import BaseEmbedder, BaseLLM
from qskill.skills.batch_integration import BatchSkillIntegrator

# Alias for backward compatibility
SkillIntegrator = BatchSkillIntegrator


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
    value_alpha = skill_config.get("value_alpha", 0.5)
    value_beta = skill_config.get("value_beta", 0.0)
    value_lambda = skill_config.get("value_lambda", 0.5)
    retrieve_general = skill_config.get("retrieve_general", 1)
    retrieve_task_specific = skill_config.get("retrieve_task_specific", 1)
    retrieve_common_mistakes = skill_config.get("retrieve_common_mistakes", 1)
    summarize_task_description = skill_config.get("summarize_task_description", False)
    enable_culling = skill_config.get("enable_culling", False)
    max_skills = skill_config.get("max_skills", 50)
    cull_threshold = skill_config.get("cull_threshold", 0.3)
    cull_batch_size = skill_config.get("cull_batch_size", 5)
    cull_min_usage = skill_config.get("cull_min_usage", 3)
    enable_merging = skill_config.get("enable_merging", False)
    merge_similarity_threshold = skill_config.get("merge_similarity_threshold", 0.85)
    rrf_k = skill_config.get("rrf_k", 60.0)
    benchmark = skill_config.get("benchmark", "markdown")

    return BatchSkillIntegrator(
        llm=llm,
        embedder=embedder,
        extract_interval=extract_interval,
        trajectory_dir="trajectories",
        skills_dir=storage_dir,
        benchmark=benchmark,
        retrieval_method=retrieval_method,
        value_alpha=value_alpha,
        value_beta=value_beta,
        value_lambda=value_lambda,
        retrieve_general=retrieve_general,
        retrieve_task_specific=retrieve_task_specific,
        retrieve_common_mistakes=retrieve_common_mistakes,
        summarize_task_description=summarize_task_description,
        enable_culling=enable_culling,
        max_skills=max_skills,
        cull_threshold=cull_threshold,
        cull_batch_size=cull_batch_size,
        cull_min_usage=cull_min_usage,
        enable_merging=enable_merging,
        merge_similarity_threshold=merge_similarity_threshold,
        rrf_k=rrf_k,
    )
