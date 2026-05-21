#!/usr/bin/env python3
"""
Test script for running a small sample of BigCodeBench tasks.
- Randomly selects N tasks from the training set
- Runs the agent on each task with code generation
- Outputs: success/failure, code, extracted skills, token consumption
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
from qskill.run.bcb_runner import BCBRunner, BCBSelection


@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_id: str
    task_description: str
    success: bool
    code: str = ""
    raw_response: str = ""
    retrieved_skills: List[str] = field(default_factory=list)
    skill_value_changes: Dict[str, Dict[str, float]] = field(default_factory=dict)
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None


class TokenTracker:
    """Tracks token usage by intercepting LLM calls."""

    def __init__(self):
        self.total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.call_count = 0

    def record_usage(self, usage: Dict[str, Any]):
        """Record token usage from an LLM response."""
        self.total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self.total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
        self.total_usage["total_tokens"] += usage.get("total_tokens", 0)
        self.call_count += 1

    def get_summary(self) -> Dict[str, Any]:
        return {
            **self.total_usage,
            "llm_calls": self.call_count
        }


class BCBTestRunner:
    """Simplified runner for testing BCB with a small sample of tasks."""

    def __init__(
        self,
        config_path: str,
        num_tasks: int = 10,
        random_seed: int = 42,
        disable_memory: bool = False,
        disable_skills: bool = False,
    ):
        self.project_root = project_root
        self.num_tasks = num_tasks
        self.random_seed = random_seed
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
        self.token_tracker = TokenTracker()

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

        # Selection configuration
        self.selection = BCBSelection(
            subset="hard",
            split="instruct",
            train_ratio=0.7,
            seed=self.random_seed,
        )

        # Load BCB data and select random tasks
        from qskill.bigcodebench_eval.task_wrappers import load_bcb_data, split_dataset
        self.problems = load_bcb_data(subset=self.selection.subset, data_path=self.selection.data_path)
        self.train_ids, _ = split_dataset(
            self.problems,
            train_ratio=self.selection.train_ratio,
            seed=self.selection.seed,
            split_file=self.selection.split_file,
        )
        self.selected_task_ids = self._select_random_tasks()

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

    def _select_random_tasks(self) -> List[str]:
        """Select random tasks from the training set."""
        if len(self.train_ids) <= self.num_tasks:
            selected = self.train_ids
        else:
            selected = random.sample(self.train_ids, k=self.num_tasks)

        print(f"\n{'='*60}")
        print(f"Selected {len(selected)} random tasks from {len(self.train_ids)} total training tasks")
        print(f"{'='*60}\n")

        return selected

    def _get_task_type(self, task: Dict[str, Any]) -> str:
        """Get task type from BCB task for skill retrieval."""
        entry_point = task.get("entry_point", "unknown")
        libs = task.get("libs", [])
        if isinstance(libs, list) and libs:
            return f"{libs[0]}/{entry_point}"
        return f"bcb/{entry_point}"

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

    def run_single_task(self, task_id: str) -> TaskResult:
        """Run a single task and return the result."""
        result = TaskResult(
            task_id=task_id,
            task_description="",
            success=False,
        )

        print(f"\n{'='*60}")
        print(f"Starting Task: {task_id}")
        print(f"{'='*60}")

        try:
            from qskill.bigcodebench_eval.task_wrappers import get_prompt
            from qskill.bigcodebench_eval.bcb_adapter import extract_code_from_response

            task = self.problems[task_id]
            prompt = get_prompt(task, split=self.selection.split)
            result.task_description = prompt[:500] + "..." if len(prompt) > 500 else prompt

            print(f"Task (truncated):\n{prompt[:300]}...")

            # Get task type
            task_type = self._get_task_type(task)

            # Retrieve skills
            retrieved_skills = []
            if self.skill_integrator:
                retrieved_skills = self.skill_integrator.retrieve_skills(
                    task_description=prompt,
                    task_type=task_type,
                    observation=None,
                )
                if retrieved_skills:
                    print(f"\nRetrieved {len(retrieved_skills)} relevant skills for this task")
                    result.retrieved_skills = [s.get("name", "") for s in retrieved_skills if s.get("name")]

            # Format skill context
            skill_context = ""
            if self.skill_integrator and retrieved_skills:
                skill_context = self.skill_integrator.format_skills_for_context(retrieved_skills)

            # Generate code
            raw_response = self.llm_provider.generate(
                messages=[
                    {"role": "system", "content": f"You are an expert Python programmer solving BigCodeBench coding tasks.\n\n{skill_context}"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.cfg.llm.temperature,
                max_tokens=self.cfg.llm.max_tokens,
            )
            result.raw_response = raw_response
            code = extract_code_from_response(raw_response)
            result.code = code

            print(f"\nGenerated code (first 200 chars):\n{code[:200]}...")

            # Evaluate
            eval_res = self._evaluate_one(task, code)
            result.success = eval_res.get("status") == "PASS"

            print(f"\n{'='*40}")
            print(f"Task {'SUCCEEDED' if result.success else 'FAILED'}")
            print(f"Status: {eval_res.get('status')}")
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
                    {"role": "assistant", "content": raw_response},
                ]
                try:
                    self.skill_integrator.extract_and_save_skill(
                        trajectory=trajectory,
                        task_description=prompt,
                        task_type=task_type,
                        success=True,
                    )
                    print("\nSkill extraction triggered for successful task")
                except Exception as e:
                    print(f"\nSkill extraction failed: {e}")

        except Exception as e:
            result.error = str(e)
            print(f"\nError executing task: {e}")

        return result

    def _evaluate_one(self, task: Dict[str, Any], code: str) -> Dict[str, Any]:
        """Evaluate one solution."""
        from qskill.bigcodebench_eval.eval_utils import sanitize_code, run_untrusted_check_with_hard_timeout

        task_id = str(task.get("task_id", "unknown"))
        entry_point = str(task.get("entry_point", "task_func"))
        test_code = str(task.get("test", "") or "")

        if not test_code:
            return {"task_id": task_id, "status": "SYNTAX_OK", "error": "no_test_code"}

        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            return {"task_id": task_id, "status": "SYNTAX_ERROR", "error": str(e)}

        clean_code = sanitize_code(code, entry_point)

        from bigcodebench.eval import PASS, FAIL, TIMEOUT
        stat, details, err, hard_timed_out = run_untrusted_check_with_hard_timeout(
            code=clean_code,
            test_code=test_code,
            entry_point=entry_point,
            max_as_limit=30 * 1024,
            max_data_limit=30 * 1024,
            max_stack_limit=10,
            min_time_limit=1.0,
            gt_time_limit=60.0,
            hard_timeout_s=120.0,
        )

        if hard_timed_out:
            return {"task_id": task_id, "status": "TIMEOUT", "error": err or "hard_timeout"}
        if err:
            return {"task_id": task_id, "status": "RUNTIME_ERROR", "error": err}
        if stat == PASS:
            return {"task_id": task_id, "status": "PASS"}
        if stat == TIMEOUT:
            return {"task_id": task_id, "status": "TIMEOUT", "error": "timeout"}
        if stat == FAIL:
            return {"task_id": task_id, "status": "FAIL", "error": str(details)[:500] if details else "fail"}
        return {"task_id": task_id, "status": "UNKNOWN", "error": str(stat)}

    def run(self) -> List[TaskResult]:
        """Run all selected tasks."""
        results = []

        print("\n" + "="*60)
        print("  BigCodeBench Test Runner")
        print("="*60)
        print(f"Number of tasks: {self.num_tasks}")
        print(f"Random seed: {self.random_seed}")
        print(f"Memory: {'Disabled' if isinstance(self.memory_service, NullMemoryService) else 'Enabled'}")
        print(f"Skills: {'Disabled' if not self.skill_integrator else 'Enabled'}")
        print("="*60)

        start_time = time.time()

        for i, task_id in enumerate(self.selected_task_ids):
            print(f"\n\n{'#'*60}")
            print(f"# Task {i + 1}/{len(self.selected_task_ids)}")
            print(f"{'#'*60}")

            result = self.run_single_task(task_id)
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
            print(f"\n{i+1}. [{status}] {result.task_id}")
            if result.retrieved_skills:
                print(f"   Retrieved skills: {', '.join(result.retrieved_skills)}")
            if result.skill_value_changes:
                for skill, change in result.skill_value_changes.items():
                    print(f"   Skill '{skill}': {change['before']:.3f} -> {change['after']:.3f}")
            if result.error:
                print(f"   Error: {result.error}")

        # Save detailed results to JSON
        output_path = project_root / "test" / "bcb" / "test_results.json"
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
                    "success": r.success,
                    "code": r.code,
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
    p = argparse.ArgumentParser(description="Run BigCodeBench test with N random tasks")
    p.add_argument(
        "--config",
        type=str,
        default=str(project_root / "configs" / "rl_bcb_config.yaml"),
        help="Path to config file"
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

    runner = BCBTestRunner(
        config_path=args.config,
        num_tasks=args.num_tasks,
        random_seed=args.seed,
        disable_memory=args.disable_memory,
        disable_skills=args.disable_skills,
    )

    results = runner.run()