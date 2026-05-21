#!/usr/bin/env python3
"""
Test script for running a small sample of LLB (Lifelong Agent Bench) tasks.
- Randomly selects N tasks from the training set
- Runs the agent on each task with shell/database/kg commands
- Outputs: success/failure, response, extracted skills, token consumption
"""

import sys
import os
import json
import random
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from qskill.configs.config import MempConfig
from qskill.providers.llm import OpenAILLM
from qskill.providers.embedding import OpenAIEmbedder
from qskill.service.base_memory_service import BaseMemoryService, NullMemoryService
from qskill.service.memory_service import MemoryService
from qskill.service.strategies import BuildStrategy, RetrieveStrategy, UpdateStrategy, StrategyConfiguration
from qskill.skills.integration import create_skill_integrator


@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_id: str
    task_description: str
    task_type: str
    success: bool
    response: str = ""
    retrieved_skills: List[str] = field(default_factory=list)
    skill_value_changes: Dict[str, Dict[str, float]] = field(default_factory=dict)
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None


class LLBTestRunner:
    """Simplified runner for testing LLB with a small sample of tasks."""

    def __init__(
        self,
        config_path: str,
        split_file: str,
        task: str = "db",
        num_tasks: int = 10,
        random_seed: int = 42,
        disable_memory: bool = False,
        disable_skills: bool = False,
    ):
        self.project_root = project_root
        self.num_tasks = num_tasks
        self.random_seed = random_seed
        self.split_file = split_file
        self.task = task
        random.seed(random_seed)

        # Load configuration
        self.config = MempConfig.from_yaml(str(config_path))
        self.cfg = self.config

        # Setup LLM and embedding providers
        self.llm_provider = OpenAILLM(
            api_key=self.cfg.llm.api_key,
            base_url=self.cfg.llm.base_url,
            model=self.cfg.llm.model,
            default_temperature=self.cfg.llm.temperature,
            default_max_tokens=self.cfg.llm.max_tokens,
            token_log_dir=str(project_root / "test" / "token_logs"),
        )

        self.embedding_provider = OpenAIEmbedder(
            api_key=self.cfg.embedding.api_key,
            base_url=self.cfg.embedding.base_url,
            model=self.cfg.embedding.model,
            max_text_len=getattr(self.cfg.embedding, "max_text_len", 4096),
            token_log_dir=str(project_root / "test" / "token_logs"),
        )

        # Token tracker
        self.call_count = 0
        self.total_tokens = 0

        # Setup memory service
        if disable_memory:
            self.memory_service = NullMemoryService()
        else:
            mos_config = self._create_mos_config()
            mos_config_path = project_root / "test" / "mos_config.json"
            mos_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(mos_config_path, "w", encoding="utf-8") as f:
                json.dump(mos_config, f)

            build_strategy = BuildStrategy(self.cfg.memory.build_strategy)
            retrieve_strategy = RetrieveStrategy(self.cfg.memory.retrieve_strategy)
            update_strategy = UpdateStrategy(self.cfg.memory.update_strategy)

            self.memory_service = MemoryService(
                mos_config_path=str(mos_config_path),
                llm_provider=self.llm_provider,
                embedding_provider=self.embedding_provider,
                strategy_config=StrategyConfiguration(build_strategy, retrieve_strategy, update_strategy),
                user_id=f"test_{os.getpid()}",
                num_workers=1,
                max_keywords=self.cfg.memory.max_keywords,
                add_similarity_threshold=getattr(self.cfg.memory, "add_similarity_threshold", 0.9),
                enable_value_driven=self.cfg.experiment.enable_value_driven,
                rl_config=self.cfg.rl_config,
                db_max_concurrency=4,
                sim_norm_mean=getattr(self.cfg.memory, "sim_norm_mean", None),
                sim_norm_std=getattr(self.cfg.memory, "sim_norm_std", None),
            )

        # Setup skill integrator
        self.skill_integrator = None
        if not disable_skills:
            self.skill_integrator = create_skill_integrator(
                config_dict={"skill": self.cfg.skill.model_dump() if hasattr(self.cfg, "skill") else {}},
                llm=self.llm_provider,
                embedder=self.embedding_provider,
            )
            if self.skill_integrator:
                print(f"Batch skill layer enabled (extract_interval={self.cfg.skill.extract_interval})")

        # Load LLB data
        self.tasks = self._load_tasks()
        self.selected_tasks = self._select_random_tasks()

    def _create_mos_config(self) -> Dict[str, Any]:
        """Create MemOS configuration."""
        return {
            "chat_model": {
                "backend": "openai",
                "config": {
                    "model_name_or_path": self.cfg.llm.model,
                    "api_key": self.cfg.llm.api_key,
                    "api_base": self.cfg.llm.base_url,
                },
            },
            "mem_reader": {
                "backend": "simple_struct",
                "config": {
                    "llm": {
                        "backend": "openai",
                        "config": {
                            "model_name_or_path": self.cfg.llm.model,
                            "api_key": self.cfg.llm.api_key,
                            "api_base": self.cfg.llm.base_url,
                        },
                    },
                    "embedder": {
                        "backend": "universal_api",
                        "config": {
                            "provider": "openai",
                            "model_name_or_path": self.cfg.embedding.model,
                            "api_key": self.cfg.embedding.api_key,
                            "base_url": self.cfg.embedding.base_url,
                        },
                    },
                    "chunker": {"backend": "sentence", "config": {"chunk_size": 500}},
                },
            },
            "user_manager": {"backend": "sqlite", "config": {"db_path": ":memory:"}},
            "top_k": 5,
        }

    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Load LLB tasks from split file."""
        if not self.split_file or not Path(self.split_file).exists():
            raise FileNotFoundError(f"LLB split file not found: {self.split_file}")

        import json
        with open(self.split_file, "r") as f:
            data = json.load(f)

        print(f"\nLoaded {len(data)} LLB tasks")
        return data

    def _detect_task_type(self, instruction: str) -> str:
        """Detect task type from instruction keywords."""
        instruction_lower = instruction.lower()

        # LLB task type keywords
        keywords = {
            "llb/db": ["sql", "database", "query", "table", "select", "insert", "update", "delete"],
            "llb/os": ["shell", "bash", "command", "file", "directory", "ls", "cd", "mkdir", "grep", "awk"],
            "llb/kg": ["knowledge graph", "sparql", "rdf", "ontology", "triple", "entity", "relation"],
        }

        for task_type, type_keywords in keywords.items():
            if any(kw in instruction_lower for kw in type_keywords):
                return task_type

        return "llb/other"

    def _select_random_tasks(self) -> List[Dict[str, Any]]:
        """Select random tasks from the training set."""
        if len(self.tasks) <= self.num_tasks:
            selected = self.tasks
        else:
            selected = random.sample(self.tasks, k=self.num_tasks)

        print(f"\n{'='*60}")
        print(f"Selected {len(selected)} random tasks from {len(self.tasks)} total tasks")
        print(f"{'='*60}\n")

        return selected

    def _get_skill_value(self, all_skills: Dict[str, Any], skill_name: str) -> float:
        """Get skill value by name from skills index."""
        for skill in all_skills.get("general_skills", []):
            if skill.get("name") == skill_name:
                return skill.get("skill_value", 0.0)
        for task_type, skills in all_skills.get("task_specific_skills", {}).items():
            for skill in skills:
                if skill.get("name") == skill_name:
                    return skill.get("skill_value", 0.0)
        for skill in all_skills.get("common_mistakes", []):
            if skill.get("name") == skill_name:
                return skill.get("skill_value", 0.0)
        return 0.0

    def run_single_task(self, idx: int, task: Dict[str, Any]) -> TaskResult:
        """Run a single task and return the result."""
        task_id = str(task.get("id", idx))
        instruction = str(task.get("instruction", task.get("question", "")))

        result = TaskResult(
            task_id=task_id,
            task_description=instruction[:500] + "..." if len(instruction) > 500 else instruction,
            task_type=self._detect_task_type(instruction),
            success=False,
        )

        print(f"\n{'='*60}")
        print(f"Starting Task: {task_id}")
        print(f"Task Type: {result.task_type}")
        print(f"{'='*60}")

        try:
            print(f"Instruction (truncated):\n{instruction[:300]}...")

            # Retrieve skills
            retrieved_skills = []
            if self.skill_integrator:
                retrieved_skills = self.skill_integrator.retrieve_skills(
                    task_description=instruction,
                    task_type=result.task_type,
                    observation=None,
                )
                if retrieved_skills:
                    print(f"\nRetrieved {len(retrieved_skills)} relevant skills for this task")
                    result.retrieved_skills = [s.get("name", "") for s in retrieved_skills if s.get("name")]

            # Format skill context
            skill_context = ""
            if self.skill_integrator and retrieved_skills:
                skill_context = self.skill_integrator.format_skills_for_context(retrieved_skills)

            # Build prompt
            from qskill.lifelongbench_eval.prompts import build_llb_prompt_with_memory, build_llb_system_prompt

            system_prompt = build_llb_system_prompt(task=self.task)
            prompt = build_llb_prompt_with_memory(instruction, memory_context=skill_context)

            # Generate response
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = self.llm_provider.generate(
                messages=messages,
                temperature=self.cfg.llm.temperature,
                max_tokens=self.cfg.llm.max_tokens,
            )
            result.response = response

            print(f"\nGenerated response (first 300 chars):\n{response[:300]}...")

            # For LLB, we consider it successful if the response is non-empty and reasonable
            # In a full evaluation, this would run the actual command and check results
            result.success = len(response.strip()) > 0 and "error" not in response.lower()[:100]

            print(f"\n{'='*40}")
            print(f"Task {'SUCCEEDED' if result.success else 'FAILED'}")
            print(f"{'='*40}")

            # Update skill values
            if self.skill_integrator and result.retrieved_skills:
                skill_value_changes = {}
                all_skills_before = self.skill_integrator.get_all_skills()
                for skill_name in result.retrieved_skills:
                    skill_value_changes[skill_name] = {"before": self._get_skill_value(all_skills_before, skill_name)}
                for skill_name in result.retrieved_skills:
                    self.skill_integrator.update_skill_value_by_name(skill_name, result.success)
                all_skills_after = self.skill_integrator.get_all_skills()
                for skill_name in result.retrieved_skills:
                    skill_value_changes[skill_name]["after"] = self._get_skill_value(all_skills_after, skill_name)
                result.skill_value_changes = skill_value_changes
                print(f"\nSkill value changes: {skill_value_changes}")

            # Extract skill from successful trajectory
            if self.skill_integrator and result.success:
                trajectory = [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": response},
                ]
                try:
                    self.skill_integrator.extract_and_save_skill(
                        trajectory=trajectory,
                        task_description=instruction,
                        task_type=result.task_type,
                        success=True,
                    )
                    print("\nSkill extraction triggered for successful task")
                except Exception as e:
                    print(f"\nSkill extraction failed: {e}")

        except Exception as e:
            result.error = str(e)
            print(f"\nError executing task: {e}")

        return result

    def run(self) -> List[TaskResult]:
        """Run all selected tasks."""
        results = []

        print("\n" + "="*60)
        print("  Lifelong Agent Bench (LLB) Test Runner")
        print("="*60)
        print(f"Task type: {self.task}")
        print(f"Number of tasks: {self.num_tasks}")
        print(f"Random seed: {self.random_seed}")
        print(f"Split file: {self.split_file}")
        print(f"Memory: {'Disabled' if isinstance(self.memory_service, NullMemoryService) else 'Enabled'}")
        print(f"Skills: {'Disabled' if not self.skill_integrator else 'Enabled'}")
        print("="*60)

        start_time = time.time()

        for i, task in enumerate(self.selected_tasks):
            print(f"\n\n{'#'*60}")
            print(f"# Task {i + 1}/{len(self.selected_tasks)}")
            print(f"{'#'*60}")

            result = self.run_single_task(i, task)
            results.append(result)

        elapsed_time = time.time() - start_time

        # Print summary
        self._print_summary(results, elapsed_time)

        return results

    def _print_summary(self, results: List[TaskResult], elapsed_time: float):
        """Print final summary of all task results."""
        print(f"\n{'─'*60}")
        print("  FINAL SUMMARY")
        print(f"{'─'*60}")

        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        print(f"Tasks Run: {len(results)}")
        print(f"Successful: {success_count} ({success_count/len(results)*100:.1f}%)")
        print(f"Failed: {fail_count} ({fail_count/len(results)*100:.1f}%)")
        print(f"Time Elapsed: {elapsed_time:.1f}s")
        print(f"Average Time per Task: {elapsed_time/len(results):.1f}s")

        # Per-task summary
        print(f"\n{'─'*60}")
        print("  PER-TASK RESULTS")
        print(f"{'─'*60}")

        for i, result in enumerate(results):
            status = "✓ SUCCESS" if result.success else "✗ FAILURE"
            print(f"\n{i+1}. [{status}] {result.task_id} ({result.task_type})")
            if result.retrieved_skills:
                print(f"   Retrieved skills: {', '.join(result.retrieved_skills)}")
            if result.skill_value_changes:
                for skill, change in result.skill_value_changes.items():
                    print(f"   Skill '{skill}': {change['before']:.3f} -> {change['after']:.3f}")
            if result.error:
                print(f"   Error: {result.error}")

        # Save detailed results to JSON
        output_path = project_root / "test" / "llb" / "test_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_data = {
            "summary": {
                "total_tasks": len(results),
                "successful": success_count,
                "failed": fail_count,
                "success_rate": success_count / len(results) if results else 0,
                "elapsed_time": elapsed_time,
            },
            "tasks": [
                {
                    "task_id": r.task_id,
                    "task_description": r.task_description,
                    "task_type": r.task_type,
                    "success": r.success,
                    "response": r.response,
                    "retrieved_skills": r.retrieved_skills,
                    "skill_value_changes": r.skill_value_changes,
                    "error": r.error,
                }
                for r in results
            ]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\nDetailed results saved to: {output_path}")


def parse_args():
    import argparse
    p = argparse.ArgumentParser(description="Run LLB test with N random tasks")
    p.add_argument(
        "--config",
        type=str,
        default=str(project_root / "configs" / "rl_llb_config.yaml"),
        help="Path to config file"
    )
    p.add_argument(
        "--split_file",
        type=str,
        required=True,
        help="Path to LLB split JSON file"
    )
    p.add_argument(
        "--task",
        type=str,
        default="db",
        choices=["db", "os", "kg"],
        help="LLB task type (db/os/kg)"
    )
    p.add_argument(
        "--num_tasks",
        type=int,
        default=10,
        help="Number of random tasks to run (default: 10)"
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    p.add_argument(
        "--disable_memory",
        action="store_true",
        help="Disable memory retrieval"
    )
    p.add_argument(
        "--disable_skills",
        action="store_true",
        help="Disable skill layer"
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    runner = LLBTestRunner(
        config_path=args.config,
        split_file=args.split_file,
        task=args.task,
        num_tasks=args.num_tasks,
        random_seed=args.seed,
        disable_memory=args.disable_memory,
        disable_skills=args.disable_skills,
    )

    results = runner.run()