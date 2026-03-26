"""
Generate Claude-style skills for ALFWorld agent using o3 API.

Claude-style skills have these characteristics:
1. Concise and actionable - focus on what to do, not verbose descriptions
2. General principles - transferable across similar tasks
3. Failure-aware - include common pitfalls and how to avoid them
4. Hierarchical - general skills + task-specific skills

Output format:
{
    "general_skills": [
        {
            "skill_id": "...",
            "title": "...",  # Short title
            "principle": "...",  # The core insight/rule
            "when_to_apply": "...",  # Triggering condition
            "example": "..."  # Brief concrete example (optional)
        }
    ],
    "task_specific_skills": {
        "pick_and_place": [...],
        "look_at_obj_in_light": [...],
        "clean": [...],
        "heat": [...],
        "cool": [...],
        "examine": [...]
    },
    "common_mistakes": [
        {
            "mistake_id": "...",
            "description": "...",  # What the mistake is
            "why_it_happens": "...",  # Why agents make this mistake
            "how_to_avoid": "..."  # Concrete fix
        }
    ]
}
"""


"""You are an expert at distilling agent behavior patterns into concise, actionable skills.

Analyze these successful and failed trajectories from an embodied AI agent operating in household environments (ALFWorld).

SUCCESSFUL TRAJECTORIES:
{success_patterns}

FAILED TRAJECTORIES:
{failure_patterns}

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


"""You are an expert at distilling agent behavior patterns into concise, actionable skills.

Task Type: {task_type.upper()}
Description: {task_descriptions.get(task_type, '')}

SUCCESSFUL TRAJECTORIES:
{success_patterns}

FAILED TRAJECTORIES:
{failure_patterns}

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



"""You are an expert at analyzing agent failures and distilling them into avoidable mistakes.

Analyze these failure patterns from an embodied AI agent:

{failure_data}

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
