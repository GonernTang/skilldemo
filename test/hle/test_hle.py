#!/usr/bin/env python3
"""
Test script for running a small sample of HLE tasks.
- Randomly selects N tasks from the training set
- Runs the agent on each task with reasoning + answer
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

import pandas as pd

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
    extracted_answer: str = ""
    correct_answer: str = ""
    retrieved_skills: List[str] = field(default_factory=list)
    skill_value_changes: Dict[str, Dict[str, float]] = field(default_factory=dict)
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None


class HLETestRunner:
    """Simplified runner for testing HLE with a small sample of tasks."""

    def __init__(
        self,
        config_path: str,
        train_path: str,
        num_tasks: int = 10,
        random_seed: int = 42,
        disable_memory: bool = False,
        disable_skills: bool = False,
    ):
        self.project_root = project_root
        self.num_tasks = num_tasks
        self.random_seed = random_seed
        self.train_path = train_path
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

        # Load data
        self.df = self._load_data()
        self.selected_rows = self._select_random_tasks()

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

    def _load_data(self) -> pd.DataFrame:
        """Load HLE dataset."""
        if not self.train_path or not Path(self.train_path).exists():
            raise FileNotFoundError(f"HLE train data not found: {self.train_path}")

        df = pd.read_parquet(self.train_path)
        print(f"\nLoaded {len(df)} HLE tasks")
        return df

    def _detect_task_type(self, question: str) -> str:
        """Detect task type from question keywords."""
        question_lower = question.lower()

        # HLE task type keywords
        keywords = {
            "hle/cs": ["computer science", "ai", "machine learning", "algorithm", "neural network", "deep learning"],
            "hle/math": ["math", "equation", "calculate", "calculus", "algebra", "geometry", "probability"],
            "hle/biology": ["biology", "bio", "cell", "organism", "genetics", "evolution"],
            "hle/physics": ["physics", "force", "energy", "motion", "quantum", "electromagnetic"],
            "hle/chemistry": ["chemistry", "chemical", "molecule", "reaction", "organic", "periodic"],
            "hle/engineering": ["engineering", "circuit", "signal", "system", "mechanical", "structural"],
            "hle/humanities": ["history", "philosophy", "literature", "economics", "sociology", "psychology"],
        }

        for task_type, type_keywords in keywords.items():
            if any(kw in question_lower for kw in type_keywords):
                return task_type

        return "hle/other"

    def _select_random_tasks(self) -> pd.DataFrame:
        """Select random tasks from the training set."""
        if len(self.df) <= self.num_tasks:
            selected = self.df
        else:
            selected = self.df.sample(n=self.num_tasks, random_state=self.random_seed)

        print(f"\n{'='*60}")
        print(f"Selected {len(selected)} random tasks from {len(self.df)} total tasks")
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

    def _build_prompt(self, question: str, is_multiple_choice: bool = False) -> str:
        """Build prompt for HLE task."""
        if is_multiple_choice:
            prompt = (
                "Your response should be in the following format:\n"
                "Explanation: {your explanation for your answer choice}\n"
                "Answer: {your chosen answer}\n"
                "Confidence: {your confidence score between 0% and 100% for your answer}\n\n"
                f"Question: {question}"
            )
        else:
            prompt = (
                "Your response should be in the following format:\n"
                "Explanation: {your explanation for your final answer}\n"
                "Exact Answer: {your succinct, final answer}\n"
                "Confidence: {your confidence score between 0% and 100% for your answer}\n\n"
                f"Question: {question}"
            )
        return prompt

    def run_single_task(self, idx: int, row: pd.Series) -> TaskResult:
        """Run a single task and return the result."""
        task_id = str(row.get("id", idx))
        question = str(row.get("question", ""))
        answer = str(row.get("answer", ""))

        result = TaskResult(
            task_id=task_id,
            task_description=question[:500] + "..." if len(question) > 500 else question,
            task_type=self._detect_task_type(question),
            success=False,
            correct_answer=answer,
        )

        print(f"\n{'='*60}")
        print(f"Starting Task: {task_id}")
        print(f"Task Type: {result.task_type}")
        print(f"{'='*60}")

        try:
            print(f"Question (truncated):\n{question[:300]}...")

            # Check if multiple choice
            is_multiple_choice = "answer" in row and any(
                c in str(row.get("question", "")).lower()
                for c in ["a)", "b)", "c)", "d)", "(a)", "(b)", "(c)", "(d)"]
            )

            # Retrieve skills
            retrieved_skills = []
            if self.skill_integrator:
                retrieved_skills = self.skill_integrator.retrieve_skills(
                    task_description=question,
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
            prompt = self._build_prompt(question, is_multiple_choice)

            # Generate response
            messages = []
            if skill_context:
                messages.append({"role": "system", "content": skill_context})
            messages.append({"role": "user", "content": prompt})

            response = self.llm_provider.generate(
                messages=messages,
                temperature=self.cfg.llm.temperature,
                max_tokens=self.cfg.llm.max_tokens,
            )
            result.response = response

            print(f"\nGenerated response (first 300 chars):\n{response[:300]}...")

            # Extract answer
            result.extracted_answer = self._extract_answer(response)

            # Judge correctness
            result.success = self._judge_answer(result.extracted_answer, answer)

            print(f"\n{'='*40}")
            print(f"Task {'SUCCEEDED' if result.success else 'FAILED'}")
            print(f"Extracted: {result.extracted_answer[:100]}...")
            print(f"Correct:   {answer[:100]}...")
            print(f"{'='*40}")

            # Update skill values using LQRL
            if self.skill_integrator and result.retrieved_skills:
                skill_value_changes = {}
                all_skills_before = self.skill_integrator.get_all_skills()
                for skill_name in result.retrieved_skills:
                    skill_value_changes[skill_name] = {"before": self._get_skill_value(all_skills_before, skill_name)}

                if result.success:
                    # Task succeeded - standard Q-learning update
                    for skill_name in result.retrieved_skills:
                        self.skill_integrator.update_skill_value_by_name(skill_name, success=True)
                else:
                    # Task failed - use LQRL with r_learning evaluation
                    actual_error = str(result.judge_result.get("feedback", ""))[:1000] if hasattr(result, 'judge_result') else "HLE task failed"
                    for skill_name in result.retrieved_skills:
                        lqrl_result = self.skill_integrator.process_task_failure_and_update(
                            skill_name=skill_name,
                            actual_error=actual_error,
                            task_context=question[:500] if question else "",
                        )
                        skill_value_changes[skill_name]["r_learning"] = lqrl_result.get("r_learning", 0.0)
                        skill_value_changes[skill_name]["quality"] = lqrl_result.get("quality", 0.0)
                        skill_value_changes[skill_name]["action"] = lqrl_result.get("action", "unknown")

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
                        task_description=question,
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

    def _extract_answer(self, response: str) -> str:
        """Extract answer from LLM response."""
        # Try to extract "Exact Answer: ..." or "Answer: ..."
        import re

        # Try Exact Answer first
        match = re.search(r"Exact Answer:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Try Answer
        match = re.search(r"Answer:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Fallback: return full response
        return response.strip()

    def _judge_answer(self, extracted: str, correct: str) -> bool:
        """Judge if extracted answer matches correct answer."""
        extracted = extracted.lower().strip()
        correct = correct.lower().strip()

        # Exact match
        if extracted == correct:
            return True

        # Try numeric comparison for math problems
        try:
            extracted_num = float(extracted)
            correct_num = float(correct)
            return abs(extracted_num - correct_num) < 1e-6
        except (ValueError, TypeError):
            pass

        # Partial match (extracted is contained in correct or vice versa)
        if extracted in correct or correct in extracted:
            return True

        return False

    def run(self) -> List[TaskResult]:
        """Run all selected tasks."""
        results = []

        print("\n" + "="*60)
        print("  HLE Test Runner")
        print("="*60)
        print(f"Number of tasks: {self.num_tasks}")
        print(f"Random seed: {self.random_seed}")
        print(f"Data source: {self.train_path}")
        print(f"Memory: {'Disabled' if isinstance(self.memory_service, NullMemoryService) else 'Enabled'}")
        print(f"Skills: {'Disabled' if not self.skill_integrator else 'Enabled'}")
        print("="*60)

        start_time = time.time()

        for i, (idx, row) in enumerate(self.selected_rows.iterrows()):
            print(f"\n\n{'#'*60}")
            print(f"# Task {i + 1}/{len(self.selected_rows)}")
            print(f"{'#'*60}")

            result = self.run_single_task(idx, row)
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
        output_path = project_root / "test" / "hle" / "test_results.json"
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
                    "extracted_answer": r.extracted_answer,
                    "correct_answer": r.correct_answer,
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
    p = argparse.ArgumentParser(description="Run HLE test with N random tasks")
    p.add_argument(
        "--config",
        type=str,
        default=str(project_root / "configs" / "rl_hle_config.yaml"),
        help="Path to config file"
    )
    p.add_argument(
        "--train",
        type=str,
        required=True,
        help="Path to HLE train parquet file"
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

    runner = HLETestRunner(
        config_path=args.config,
        train_path=args.train,
        num_tasks=args.num_tasks,
        random_seed=args.seed,
        disable_memory=args.disable_memory,
        disable_skills=args.disable_skills,
    )

    results = runner.run()