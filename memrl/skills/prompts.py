"""Prompt templates for skill extraction and retrieval."""

# =============================================================================
# Skill Extraction Prompts
# =============================================================================

GENERAL_SKILL_EXTRACTION_PROMPT = """You are an expert at distilling agent behavior patterns into concise, actionable skills.

Analyze these successful and failed trajectories from an embodied AI agent operating in household environments (ALFWorld).

You are given {num_success} successful trajectories and {num_failure} failed trajectories.

SUCCESSFUL TRAJECTORIES:
{success_text}

FAILED TRAJECTORIES:
{failure_text}

Your task:
Based on the patterns you observe in these trajectories, extract the MOST IMPORTANT and ACTIONABLE general skills that apply across ALL task types.

Quality over quantity - only extract skills that are clearly demonstrated by the data.

Requirements for each skill:
1. **name**: Short identifier in kebab-case (e.g., "verify-object-state", "check-location-first")
2. **description**: One sentence explaining when to use this skill
3. **content**: Markdown format with:
   - ## Title (capitalized)
   - **Process:** numbered steps (be specific and actionable)
   - **Anti-patterns:** what NOT to do (at least 2 items)

Format as JSON array:
[
    {{
        "name": "skill-name-in-kebab-case",
        "description": "Use when...",
        "content": "## Skill Title\\n\\n**Process:**\\n1. Step one...\\n2. Step two...\\n\\n**Anti-patterns:**\\n- What not to do...\\n- Another mistake..."
    }}
]

Return ONLY the JSON array, no other text."""

TASK_SPECIFIC_SKILL_EXTRACTION_PROMPT = """You are an expert at distilling agent behavior patterns into concise, actionable skills.

Task Type: {task_type}
Category: {category}
Description: Tasks involving {task_description}

You are given {num_success} successful trajectories and {num_failure} failed trajectories for this task type.

SUCCESSFUL TRAJECTORIES:
{success_text}

FAILED TRAJECTORIES:
{failure_text}

Your task:
Based on the patterns you observe in these trajectories, extract the MOST IMPORTANT and ACTIONABLE skills specific to {task_type} tasks.

Quality over quantity - only extract skills that are clearly demonstrated by the data.

Requirements for each skill:
1. **name**: Short identifier in kebab-case (e.g., "heat-check-temperature", "cool-wait-fully")
2. **description**: One sentence explaining when to use this skill
3. **content**: Markdown format with:
   - ## Title (capitalized)
   - **Process:** numbered steps (be specific and actionable)
   - **Anti-patterns:** what NOT to do (at least 2 items)

Format as JSON array:
[
    {{
        "name": "skill-name-in-kebab-case",
        "description": "Use when...",
        "content": "## Skill Title\\n\\n**Process:**\\n1. Step one...\\n2. Step two...\\n\\n**Anti-patterns:**\\n- What not to do...\\n- Another mistake..."
    }}
]

Return ONLY the JSON array, no other text."""

COMMON_MISTAKES_EXTRACTION_PROMPT = """You are an expert at analyzing agent failures and distilling them into avoidable mistakes.

You are given {num_failures} failed trajectories to analyze.

{failure_text}

Your task:
Based on the failure patterns you observe, extract the MOST IMPORTANT mistakes to avoid.

Quality over quantity - only extract mistakes that are clearly demonstrated by the data.

Requirements for each mistake:
1. **name**: Short identifier in kebab-case (e.g., "assume-object-exists", "skip-verification")
2. **description**: One sentence describing this common mistake
3. **content**: Markdown format with:
   - ## Title (what NOT to do)
   - **Why it happens:** root cause analysis
   - **How to avoid:** concrete steps to prevent this mistake

Format as JSON array:
[
    {{
        "name": "mistake-name-in-kebab-case",
        "description": "Common mistake: ...",
        "content": "## Mistake Title\\n\\n**Why it happens:**\\nRoot cause...\\n\\n**How to avoid:**\\n1. Step one...\\n2. Step two..."
    }}
]

Return ONLY the JSON array, no other text."""

# =============================================================================
# Skill Retrieval Prompts
# =============================================================================

SKILL_RANKING_PROMPT = """You are a task execution assistant, skilled at matching relevant skills to tasks.

## Available Skills
{skills_text}

## Current Task
Task Description: {query}
Current Observation: {observation}

## Your Task
Read all available skills and determine which ones are relevant to the current task.
Output format:
```
Relevant Skills: skill-name-1, skill-name-2, ...
```
If no relevant skills:
```
Relevant Skills: None
```"""

# =============================================================================
# Prompt Builder Helpers
# =============================================================================

def build_general_skill_prompt(
    success_text: str,
    failure_text: str,
    num_success: int,
    num_failure: int,
) -> str:
    """Build prompt for general skill extraction."""
    return GENERAL_SKILL_EXTRACTION_PROMPT.format(
        num_success=num_success,
        num_failure=num_failure,
        success_text=success_text,
        failure_text=failure_text,
    )


def build_task_specific_skill_prompt(
    task_type: str,
    category: str,
    task_description: str,
    success_text: str,
    failure_text: str,
    num_success: int,
    num_failure: int,
) -> str:
    """Build prompt for task-specific skill extraction."""
    return TASK_SPECIFIC_SKILL_EXTRACTION_PROMPT.format(
        task_type=task_type.upper(),
        category=category,
        task_description=task_description,
        num_success=num_success,
        num_failure=num_failure,
        success_text=success_text,
        failure_text=failure_text,
    )


def build_common_mistakes_prompt(
    failure_text: str,
    num_failures: int,
) -> str:
    """Build prompt for common mistakes extraction."""
    return COMMON_MISTAKES_EXTRACTION_PROMPT.format(
        num_failures=num_failures,
        failure_text=failure_text,
    )


def build_skill_ranking_prompt(
    skills_text: str,
    query: str,
    observation: str = "N/A",
) -> str:
    """Build prompt for LLM-based skill ranking."""
    return SKILL_RANKING_PROMPT.format(
        skills_text=skills_text,
        query=query,
        observation=observation,
    )
