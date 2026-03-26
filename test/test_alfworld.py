#!/usr/bin/env python3
"""
Test script for running a small sample of ALFWorld tasks.
- Randomly selects N tasks from the training set
- Runs the agent on each task with real-time trajectory printing
- Outputs: success/failure, trajectory, extracted skills, token consumption
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
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import textworld
import textworld.gym
from alfworld.agents.environment.alfred_tw_env import AlfredTWEnv, AlfredDemangler, AlfredInfos

from memrl.configs.config import MempConfig
from memrl.providers.llm import OpenAILLM
from memrl.providers.embedding import OpenAIEmbedder
from memrl.agent.memp_agent import MempAgent
from memrl.service.base_memory_service import BaseMemoryService, NullMemoryService
from memrl.service.memory_service import MemoryService
from memrl.service.strategies import BuildStrategy, RetrieveStrategy, UpdateStrategy, StrategyConfiguration
from memrl.skills.integration import create_skill_integrator
from memrl.envs.alfworld_env import AlfWorldEnv, load_config_from_path


@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_id: str
    task_description: str
    success: bool
    trajectory: List[Dict[str, str]] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    skills_extracted: List[str] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TokenUsage:
    """Aggregated token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: 'TokenUsage'):
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens


class TokenTracker:
    """Tracks token usage by intercepting LLM calls."""

    def __init__(self):
        self.total_usage = TokenUsage()
        self.call_count = 0

    def record_usage(self, usage: Dict[str, Any]):
        """Record token usage from an LLM response."""
        self.total_usage.prompt_tokens += usage.get('prompt_tokens', 0)
        self.total_usage.completion_tokens += usage.get('completion_tokens', 0)
        self.total_usage.total_tokens += usage.get('total_tokens', 0)
        self.call_count += 1

    def get_summary(self) -> Dict[str, Any]:
        return {
            'prompt_tokens': self.total_usage.prompt_tokens,
            'completion_tokens': self.total_usage.completion_tokens,
            'total_tokens': self.total_usage.total_tokens,
            'llm_calls': self.call_count
        }


class TestRunner:
    """Simplified runner for testing ALFWorld with a small sample of tasks."""

    def __init__(
        self,
        config_path: str,
        num_tasks: int = 5,
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

        # Setup agent
        few_shot_path = project_root / self.cfg.experiment.few_shot_path
        if few_shot_path.exists():
            with open(few_shot_path, "r", encoding="utf-8") as f:
                self.few_shot_examples = json.load(f)
        else:
            print(f"Warning: Few-shot examples not found at {few_shot_path}, using empty dict")
            self.few_shot_examples = {}

        self.agent = MempAgent(
            llm_provider=self.llm_provider,
            few_shot_examples=self.few_shot_examples
        )

        # Setup skill integrator (batch mode)
        self.skill_integrator = None
        if not disable_skills:
            self.skill_integrator = create_skill_integrator(
                config_dict={'skill': self.cfg.skill.model_dump() if hasattr(self.cfg, 'skill') else {}},
                llm=self.llm_provider,
            )
            if self.skill_integrator:
                print(f"Batch skill layer enabled (extract_interval={self.cfg.skill.extract_interval})")

        # Load environment and select random tasks
        self.env_config_path = str(project_root / "configs" / "envs" / "alfworld.yaml")
        self.env_config = load_config_from_path(self.env_config_path)
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

    def _select_random_tasks(self) -> List[str]:
        """Select random tasks from the training set."""
        env_controller = AlfredTWEnv(self.env_config, train_eval="train")
        all_game_files = env_controller.game_files

        if len(all_game_files) <= self.num_tasks:
            selected = all_game_files
        else:
            selected = random.sample(all_game_files, k=self.num_tasks)

        print(f"\n{'='*60}")
        print(f"Selected {len(selected)} random tasks from {len(all_game_files)} total training games")
        print(f"{'='*60}\n")

        return selected

    def _print_separator(self, title: str = ""):
        """Print a visual separator."""
        if title:
            print(f"\n{'─'*60}")
            print(f"  {title}")
            print(f"{'─'*60}")
        else:
            print(f"\n{'─'*60}\n")

    def _extract_task_description(self, obs: str) -> str:
        """Extract clean task description from observation."""
        lines = obs.split('\n\n')
        if len(lines) > 1:
            return '\n\n'.join(lines[1:])
        return obs

    def run_single_task(self, game_file: str) -> TaskResult:
        """Run a single task and return the result."""
        task_id = game_file.split('/')[-1].replace('.json', '')
        result = TaskResult(
            task_id=task_id,
            task_description="",
            success=False,
        )

        self._print_separator(f"Starting Task: {task_id}")

        try:
            # Create environment for this single task using textworld gym
            domain_randomization = self.env_config["env"]["domain_randomization"]
            alfred_demangler = AlfredDemangler(shuffle=domain_randomization)
            wrappers = [alfred_demangler, AlfredInfos]
            request_infos = textworld.EnvInfos(won=True, admissible_commands=True, extras=["gamefile"])

            env_id = textworld.gym.register_games(
                [game_file],
                request_infos,
                batch_size=1,
                auto_reset=False,
                asynchronous=True,
                max_episode_steps=100,  # Default max steps
                wrappers=wrappers
            )
            underlying_env = textworld.gym.make(env_id)

            # Wrap with AlfWorldEnv
            env = AlfWorldEnv(
                config_path=self.env_config_path,
                preconfigured_env=underlying_env,
                batch_size=1
            )

            # Reset environment
            results = env.reset()
            initial_obs = results[0]['obs']
            task_desc = self._extract_task_description(initial_obs)
            result.task_description = task_desc

            print(f"Task Description:\n{task_desc[:500]}...")
            print()

            # Get task type
            task_type = '/'.join(results[0]['info']['extra.gamefile'].split('/')[-3:-1])

            # Retrieve memories
            if isinstance(self.memory_service, NullMemoryService):
                retrieved_mems = []
            else:
                retrieved = self.memory_service.retrieve_query(
                    task_desc,
                    k=self.cfg.memory.k_retrieve,
                    threshold=getattr(self.cfg.rl_config, 'sim_threshold', 0.0)
                )
                if isinstance(retrieved, tuple):
                    retrieved_mems = retrieved[0].get('selected', [])
                else:
                    retrieved_mems = []

            # Retrieve skills
            retrieved_skills = []
            if self.skill_integrator:
                retrieved_skills = self.skill_integrator.retrieve_skills(
                    task_description=task_desc,
                    task_type=task_type,
                    observation=initial_obs,
                    k=self.cfg.skill.retrieve_k if hasattr(self.cfg, 'skill') else 3
                )
                if retrieved_skills:
                    print(f"\nRetrieved {len(retrieved_skills)} relevant skills for this task")

            # Construct initial messages for the agent
            messages = self.agent._construct_messages(
                task_description=task_desc,
                retrieved_memories={'successed': retrieved_mems, 'failed': []},
                task_type=task_type
            )

            # Add retrieved skills to context
            if retrieved_skills:
                skills_context = self.skill_integrator.format_skills_for_context(retrieved_skills)
                if skills_context:
                    messages.append({"role": "system", "content": skills_context})

            # Main execution loop
            current_obs = initial_obs
            max_steps = self.cfg.experiment.max_steps

            for step in range(max_steps):
                print(f"\n{'='*40}")
                print(f"Step {step + 1}/{max_steps}")
                print(f"{'='*40}")

                # Get action from agent
                action = self.agent.act(
                    observation=current_obs if step > 0 else "",
                    history_messages=messages,
                    first_step=(step == 0)
                )

                if action:
                    print(f"Action: {action}")
                    result.actions.append(action)
                else:
                    print("Action: None (failed to get action)")
                    break

                # Execute action in environment
                results = env.step([action])
                step_result = results[0]

                current_obs = step_result['obs']
                reward = step_result['reward']
                done = step_result['done']

                # Clean observation for display
                clean_obs = '\n'.join(current_obs.split('\n\n')[1:]) if '\n\n' in current_obs else current_obs
                print(f"Observation (truncated):\n{clean_obs[:300]}...")

                result.observations.append(current_obs)
                result.trajectory.append({
                    "step": step + 1,
                    "action": action,
                    "observation": current_obs,
                    "reward": reward,
                    "done": done
                })

                if done:
                    result.success = reward > 0
                    print(f"\n{'='*40}")
                    print(f"Task {'SUCCEEDED' if result.success else 'FAILED'}")
                    print(f"{'='*40}")
                    break

            # Process skill layer (batch mode)
            if self.skill_integrator:
                # Convert trajectory format for batch skill extractor
                skill_trajectory = []
                for step in result.trajectory:
                    action = step.get("action", "")
                    observation = step.get("observation", "")
                    skill_trajectory.append({"action": action, "observation": observation})

                # Add trajectory to buffer - will trigger batch extraction when N reached
                batch_result = self.skill_integrator.add_trajectory(
                    trajectory=skill_trajectory,
                    task_description=task_desc,
                    task_type=task_type,
                    success=result.success,
                )

                if batch_result:
                    # Batch extraction was triggered
                    total_skills = (
                        len(batch_result.get("general_skills", [])) +
                        sum(len(v) for v in batch_result.get("task_specific_skills", {}).values())
                    )
                    result.skills_extracted = [f"batch_{total_skills}_skills"]
                    print(f"\nBatch skill extraction triggered!")
                    print(f"  General skills: {len(batch_result.get('general_skills', []))}")
                    for task_type, skills in batch_result.get("task_specific_skills", {}).items():
                        print(f"  {task_type}: {len(skills)} skills")
                    print(f"  Common mistakes: {len(batch_result.get('common_mistakes', []))}")

                pending = self.skill_integrator.pending_count
                if pending > 0:
                    print(f"  [Pending {pending} trajectories before next extraction]")

        except Exception as e:
            result.error = str(e)
            print(f"\nError executing task: {e}")

        return result

    def run(self) -> List[TaskResult]:
        """Run all selected tasks."""
        results = []

        print("\n" + "="*60)
        print("  ALFWorld Test Runner")
        print("="*60)
        print(f"Number of tasks: {self.num_tasks}")
        print(f"Random seed: {self.random_seed}")
        print(f"Memory: {'Disabled' if isinstance(self.memory_service, NullMemoryService) else 'Enabled'}")
        print(f"Skills: {'Disabled' if not self.skill_integrator else 'Enabled'}")
        print("="*60)

        # Create token log directory
        token_log_dir = project_root / "test" / "token_logs"
        token_log_dir.mkdir(parents=True, exist_ok=True)
        token_log_path = token_log_dir / "token_usage.jsonl"

        # Clear previous token log
        if token_log_path.exists():
            token_log_path.unlink()

        start_time = time.time()

        for i, game_file in enumerate(self.selected_tasks):
            print(f"\n\n{'#'*60}")
            print(f"# Task {i + 1}/{len(self.selected_tasks)}")
            print(f"{'#'*60}")

            result = self.run_single_task(game_file)
            results.append(result)

            # Read token usage so far
            if token_log_path.exists():
                with open(token_log_path, "r") as f:
                    lines = f.readlines()
                    total_prompt = 0
                    total_completion = 0
                    total_tokens = 0
                    for line in lines:
                        try:
                            entry = json.loads(line)
                            usage = entry.get('usage', {})
                            total_prompt += usage.get('prompt_tokens', 0)
                            total_completion += usage.get('completion_tokens', 0)
                            total_tokens += usage.get('total_tokens', 0)
                        except:
                            pass
                    result.token_usage = {
                        'prompt_tokens': total_prompt,
                        'completion_tokens': total_completion,
                        'total_tokens': total_tokens,
                        'llm_calls': len(lines)
                    }

        elapsed_time = time.time() - start_time

        # Print summary
        self._print_summary(results, elapsed_time)

        return results

    def _print_summary(self, results: List[TaskResult], elapsed_time: float):
        """Print final summary of all task results."""
        self._print_separator("FINAL SUMMARY")

        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        print(f"Tasks Run: {len(results)}")
        print(f"Successful: {success_count} ({success_count/len(results)*100:.1f}%)")
        print(f"Failed: {fail_count} ({fail_count/len(results)*100:.1f}%)")
        print(f"Time Elapsed: {elapsed_time:.1f}s")
        print(f"Average Time per Task: {elapsed_time/len(results):.1f}s")

        # Token summary
        total_prompt = sum(r.token_usage.get('prompt_tokens', 0) for r in results)
        total_completion = sum(r.token_usage.get('completion_tokens', 0) for r in results)
        total_tokens = sum(r.token_usage.get('total_tokens', 0) for r in results)
        total_calls = sum(r.token_usage.get('llm_calls', 0) for r in results)

        print(f"\nToken Usage:")
        print(f"  Prompt Tokens: {total_prompt:,}")
        print(f"  Completion Tokens: {total_completion:,}")
        print(f"  Total Tokens: {total_tokens:,}")
        print(f"  LLM Calls: {total_calls}")

        # Per-task summary
        self._print_separator("PER-TASK RESULTS")

        for i, result in enumerate(results):
            status = "✓ SUCCESS" if result.success else "✗ FAILURE"
            print(f"\n{i+1}. [{status}] {result.task_id}")
            print(f"   Actions taken: {len(result.actions)}")
            if result.skills_extracted:
                print(f"   Skills extracted: {', '.join(result.skills_extracted)}")
            if result.error:
                print(f"   Error: {result.error}")

        # Save detailed results to JSON
        output_path = project_root / "test" / "test_results.json"
        output_data = {
            "summary": {
                "total_tasks": len(results),
                "successful": success_count,
                "failed": fail_count,
                "success_rate": success_count / len(results) if results else 0,
                "elapsed_time": elapsed_time,
                "total_tokens": total_tokens,
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_completion,
                "total_llm_calls": total_calls,
            },
            "tasks": [
                {
                    "task_id": r.task_id,
                    "task_description": r.task_description[:500] + "..." if len(r.task_description) > 500 else r.task_description,
                    "success": r.success,
                    "actions": r.actions,
                    "trajectory": r.trajectory,
                    "skills_extracted": r.skills_extracted,
                    "token_usage": r.token_usage,
                    "error": r.error,
                }
                for r in results
            ]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\nDetailed results saved to: {output_path}")


def parse_args():
    p = argparse.ArgumentParser(description="Run ALFWorld test with N random tasks")
    p.add_argument(
        "--config",
        type=str,
        default=str(project_root / "configs" / "rl_alf_config.yaml"),
        help="Path to config file"
    )
    p.add_argument(
        "--num_tasks",
        type=int,
        default=5,
        help="Number of random tasks to run (default: 5)"
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

    runner = TestRunner(
        config_path=args.config,
        num_tasks=args.num_tasks,
        random_seed=args.seed,
        disable_memory=args.disable_memory,
        disable_skills=args.disable_skills,
    )

    results = runner.run()
