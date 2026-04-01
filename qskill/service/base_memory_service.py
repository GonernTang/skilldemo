"""
Base interface for memory services.

This module defines the contract that all memory service implementations must follow,
allowing users to plug in different implementations (e.g., real MemoryService or a no-op service).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseMemoryService(ABC):
    """
    Abstract interface for memory services.

    Implementations must provide:
    - retrieve_query: Fetch relevant memories for a task
    - add_memories: Store new memories
    - update_values: Update Q-values for stored memories
    - checkpoint management methods (optional for null implementation)
    """

    @abstractmethod
    def retrieve_query(
        self,
        task_description: str,
        k: int = 5,
        threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Retrieve memories relevant to the query.

        Args:
            task_description: Task description or query string
            k: Number of memories to retrieve
            threshold: Similarity threshold for filtering

        Returns:
            Dict with keys: "actions", "selected", "candidates", "simmax"
        """

    @abstractmethod
    def add_memories(
        self,
        task_description: str,
        trajectories: List[Dict[str, Any]],
        successes: List[bool],
        sources: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add new memories to the store.

        Args:
            task_description: Description of the task
            trajectories: List of trajectory data
            successes: List of success/failure flags
            sources: Optional list of source identifiers

        Returns:
            List of memory IDs
        """

    @abstractmethod
    def update_values(
        self,
        successes: List[bool],
        retrieved_ids_list: List[List[str]],
        rewards: Optional[List[float]] = None,
    ) -> List[float]:
        """
        Update Q-values for retrieved memories based on outcomes.

        Args:
            successes: List of success/failure for each episode
            retrieved_ids_list: List of memory ID lists (one per episode)
            rewards: Optional reward values

        Returns:
            List of updated Q-values
        """

    def load_checkpoint_snapshot(
        self,
        snapshot_dir: str,
        expected_ckpt_id: Optional[int] = None,
    ) -> int:
        """
        Load state from a checkpoint snapshot.

        Default implementation returns 0 (no checkpoint loaded).

        Args:
            snapshot_dir: Directory containing checkpoint
            expected_ckpt_id: Expected checkpoint ID for validation

        Returns:
            Checkpoint ID that was loaded, or 0 if none
        """
        return 0

    def save_checkpoint_snapshot(
        self,
        target_ck_dir: str,
        ckpt_id: int,
    ) -> Dict[str, Any]:
        """
        Save current state to a checkpoint snapshot.

        Default implementation returns empty metadata.

        Args:
            target_ck_dir: Target directory for checkpoint
            ckpt_id: Checkpoint identifier

        Returns:
            Checkpoint metadata dict
        """
        return {}


class NullMemoryService(BaseMemoryService):
    """
    A no-op memory service that returns empty results.

    Use this when you want to run agents without any memory retrieval.
    All retrieval calls return empty dict, and add/update operations
    are no-ops.

    The runner checks `isinstance(result, tuple)` to decide how to extract
    results. Returning a dict (not tuple) ensures the runner's else branch
    sets retrieved_memories=[] correctly.
    """

    def retrieve_query(
        self,
        task_description: str,
        k: int = 5,
        threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """Return empty results (no memories retrieved)."""
        return {"actions": [], "selected": [], "candidates": [], "simmax": 0.0}

    def add_memories(
        self,
        task_description: str,
        trajectories: List[Dict[str, Any]],
        successes: List[bool],
        sources: Optional[List[str]] = None,
    ) -> List[str]:
        """No-op: return empty list of memory IDs."""
        return []

    def update_values(
        self,
        successes: List[bool],
        retrieved_ids_list: List[List[str]],
        rewards: Optional[List[float]] = None,
    ) -> List[float]:
        """No-op: return empty list of Q-values."""
        return []
