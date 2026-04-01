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
Based on the patterns you observe in these trajectories, extract general skills that apply across ALL task types.

**Extract {extract_min}-{extract_max} skills based on the data quality:**
- If you see clear, distinct patterns → extract more (up to {extract_max})
- If patterns are vague or overlapping → extract fewer (as few as {extract_min})
- Quality over quantity

Requirements for each skill:
1. **name**: Short identifier in kebab-case (e.g., "verify-object-state", "check-location-first")
2. **description**: One sentence explaining when to use this skill
3. **content**: Markdown format with:
   - ## Title (capitalized)
   - **Process:** numbered steps (be specific and actionable)
   - **Anti-patterns:** what NOT to do (at least 2 items)
   - **Failure Recovery:** What to do if this process fails (specific recovery steps)

**CRITICAL: You MUST extract these skills if failure patterns exist:**
1. **Repeated Action Failure**: If the same action returns "Nothing happened" 2+ times, STOP repeating and try a different approach
2. **Surface Before Container**: Always check visible object surfaces before searching inside containers/drawers/cabinets
3. **Object Location Precision**: Objects like "toiletpaperhanger" are DIFFERENT locations from "toilet" or "sinkbasin"

Format as JSON array:
[
    {{
        "name": "skill-name-in-kebab-case",
        "description": "Use when...",
        "content": "## Skill Title\\n\\n**Process:**\\n1. Step one...\\n2. Step two...\\n\\n**Anti-patterns:**\\n- What not to do...\\n- Another mistake...\\n\\n**Failure Recovery:**\\n- If X fails, do Y instead..."
    }}
]

Return {extract_min}-{extract_max} skills as a JSON array, no other text."""

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
Based on the patterns you observe in these trajectories, extract skills specific to {task_type} tasks.

**Extract {extract_min}-{extract_max} skills based on the data quality:**
- If you see clear, distinct patterns → extract more (up to {extract_max})
- If patterns are vague or overlapping → extract fewer (as few as {extract_min})
- Quality over quantity

Requirements for each skill:
1. **name**: Short identifier in kebab-case (e.g., "heat-check-temperature", "cool-wait-fully")
2. **description**: One sentence explaining when to use this skill
3. **content**: Markdown format with:
   - ## Title (capitalized)
   - **Process:** numbered steps (be specific and actionable)
   - **Anti-patterns:** what NOT to do (at least 2 items)
   - **Failure Recovery:** What to do if this process fails

**Task-specific critical rules:**
{task_type_specific_rules}

Format as JSON array:
[
    {{
        "name": "skill-name-in-kebab-case",
        "description": "Use when...",
        "content": "## Skill Title\\n\\n**Process:**\\n1. Step one...\\n2. Step two...\\n\\n**Anti-patterns:**\\n- What not to do...\\n- Another mistake...\\n\\n**Failure Recovery:**\\n- If X fails, do Y instead..."
    }}
]

Return {extract_min}-{extract_max} skills as a JSON array, no other text."""

COMMON_MISTAKES_EXTRACTION_PROMPT = """You are an expert at analyzing agent failures and distilling them into avoidable mistakes.

You are given {num_failures} failed trajectories to analyze.

{failure_text}

Your task:
Analyze what went wrong and extract common mistakes to avoid in future similar tasks.

**Extract {extract_min}-{extract_max} mistakes based on the data quality:**
- If you see clear, distinct failure patterns → extract more (up to {extract_max})
- If failure patterns are vague or similar → extract fewer (as few as {extract_min})
- Quality over quantity

**Focus on these high-impact failure patterns:**
1. **Repeated Action Loop**: Same action repeated 3+ times → ALWAYS causes failure
2. **Missing Surface Check**: Object was on a visible surface but agent searched containers → caused failure
3. **Wrong Object Location**: Agent looked in wrong location (e.g., toilet instead of toiletpaperhanger) → caused failure
4. **No Feedback Response**: Agent ignored "Nothing happens" feedback and kept trying same approach → caused failure
5. **Incomplete Task**: Agent stopped before completing all sub-goals (e.g., heated but didn't put it) → caused failure

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

Return {extract_min}-{extract_max} mistakes as a JSON array, no other text."""

# =============================================================================
# Task Description Summarization Prompt
# =============================================================================

TASK_SUMMARIZATION_PROMPT = """You are an expert at analyzing household task descriptions and extracting the key intent.

Given the following ALFWorld task description, summarize it into a concise, specific action phrase that captures the core task.

Original Task Description:
{task_description}

Your task:
1. Identify the object(s) involved (e.g., candle, soapbar, mug)
2. Identify the target location/receptacle (e.g., toilet, countertop, cabinet)
3. Identify any special requirements (e.g., "clean", "heated", "in light")
4. Identify potential pitfalls:
   - "put a hot X" means heat X BEFORE putting it
   - "find two X" means find BOTH instances of X
   - "toiletpaperhanger" ≠ "toilet" - they are different locations
   - "cup" and "mug" may be treated as different objects

5. Output a concise summary in 5-10 words that captures the specific action

Output format:
```
Summarized Task: [concise action phrase]
Potential Issues: [any edge cases or pitfalls to watch for]
```

Examples:
- "Put a clean soapbar on the countertop" → "place clean soapbar on countertop"
- "Look at the mug under the lamp" → "examine mug in illuminated area"
- "Heat the bread in the microwave" → "heat bread using microwave"
- "put a hot cup in sidetable" → "heat cup then place in sidetable | WATCH: cup heating limitations"

Summarized Task:"""

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
# Task-Specific Critical Rules
# =============================================================================

TASK_TYPE_SPECIFIC_RULES = {
    "pick_and_place": """
**PICK_AND_PLACE Critical Rules:**
- Objects on SURFACES (dresser, coffeetable, sidetable) are visible - check them FIRST before opening containers
- "toiletpaperhanger" is a DIFFERENT location from "toilet" - if task says "toiletpaper", check toiletpaperhanger
- If "take X from Y" fails with "Nothing happened", X may be in a different location - re-scan nearby surfaces
- "put two X in Y" means you need to find and move BOTH instances of X""",

    "heat": """
**HEAT Critical Rules:**
- Objects like mug, cup, potato, apple CAN be heated - place them INSIDE the microwave/stoveburner first
- "heat X with microwave" means X should be inside the microwave, then use the heat action
- If "heat X with Y" fails (Nothing happens), verify X is actually inside Y
- After heating, you may need to "take X from microwave" before putting it somewhere""",

    "cool": """
**COOL Critical Rules:**
- "cool X with fridge" means X should be placed in the fridge, then cooled
- After cooling, you may need to "take X from fridge" before putting it somewhere
- Objects like potato, apple, tomato, pan CAN be cooled""",

    "clean": """
**CLEAN Critical Rules:**
- "clean X with Y" requires X to be in your inventory and Y (sinkbasin, bathtubbasin) to be the cleaning location
- Cloth must be cleaned before it can be used - clean it at sinkbasin or bathtubbasin""",

    "look_at_obj_in_light": """
**LOOK_AT Critical Rules:**
- Must use "look at X" action with X visible and in an illuminated area
- Some objects require specific lighting conditions to be visible""",
}


def build_general_skill_prompt(
    success_text: str,
    failure_text: str,
    num_success: int,
    num_failure: int,
    extract_min: int = 1,
    extract_max: int = 3,
) -> str:
    """Build prompt for general skill extraction.

    Args:
        success_text: Formatted success trajectories
        failure_text: Formatted failure trajectories
        num_success: Number of success trajectories
        num_failure: Number of failure trajectories
        extract_min: Minimum number of skills to extract (default: 1)
        extract_max: Maximum number of skills to extract (default: 3)
    """
    return GENERAL_SKILL_EXTRACTION_PROMPT.format(
        num_success=num_success,
        num_failure=num_failure,
        success_text=success_text,
        failure_text=failure_text,
        extract_min=extract_min,
        extract_max=extract_max,
    )


def build_task_specific_skill_prompt(
    task_type: str,
    category: str,
    task_description: str,
    success_text: str,
    failure_text: str,
    num_success: int,
    num_failure: int,
    extract_min: int = 1,
    extract_max: int = 3,
) -> str:
    """Build prompt for task-specific skill extraction.

    Args:
        task_type: Type of task (e.g., "cool", "heat")
        category: Category name
        task_description: Description of the task type
        success_text: Formatted success trajectories
        failure_text: Formatted failure trajectories
        num_success: Number of success trajectories
        num_failure: Number of failure trajectories
        extract_min: Minimum number of skills to extract (default: 1)
        extract_max: Maximum number of skills to extract (default: 3)
    """
    # Get task-specific rules, default to empty if not found
    task_rules = TASK_TYPE_SPECIFIC_RULES.get(task_type.lower(), "")

    return TASK_SPECIFIC_SKILL_EXTRACTION_PROMPT.format(
        task_type=task_type.upper(),
        category=category,
        task_description=task_description,
        num_success=num_success,
        num_failure=num_failure,
        success_text=success_text,
        failure_text=failure_text,
        extract_min=extract_min,
        extract_max=extract_max,
        task_type_specific_rules=task_rules,
    )


def build_common_mistakes_prompt(
    failure_text: str,
    num_failures: int,
    extract_min: int = 1,
    extract_max: int = 3,
) -> str:
    """Build prompt for common mistakes extraction.

    Args:
        failure_text: Formatted failure trajectories
        num_failures: Number of failure trajectories
        extract_min: Minimum number of mistakes to extract (default: 1)
        extract_max: Maximum number of mistakes to extract (default: 3)
    """
    return COMMON_MISTAKES_EXTRACTION_PROMPT.format(
        num_failures=num_failures,
        failure_text=failure_text,
        extract_min=extract_min,
        extract_max=extract_max,
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


def build_task_summarization_prompt(task_description: str) -> str:
    """Build prompt for task description summarization."""
    return TASK_SUMMARIZATION_PROMPT.format(
        task_description=task_description,
    )
