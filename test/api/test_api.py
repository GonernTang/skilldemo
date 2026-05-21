#!/usr/bin/env python3
"""
Test script to verify API connectivity.
Tests LLM and Embedding API connections using configuration files.
"""

import sys
import os
import json
import argparse
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from qskill.configs.config import MempConfig
from qskill.providers.llm import OpenAILLM
from qskill.providers.embedding import OpenAIEmbedder


class APITestRunner:
    """Test API connectivity for LLM and Embedding providers."""

    def __init__(
        self,
        config_path: str,
    ):
        self.project_root = project_root
        self.config_path = config_path

        # Load configuration
        self.config = MempConfig.from_yaml(str(config_path))
        self.cfg = self.config

    def test_llm_api(self) -> Dict[str, Any]:
        """Test LLM API connectivity."""
        print("\n" + "="*60)
        print("  Testing LLM API")
        print("="*60)

        result = {
            "success": False,
            "model": self.cfg.llm.model,
            "provider": self.cfg.llm.provider,
            "base_url": self.cfg.llm.base_url,
            "error": None,
            "latency_ms": None,
        }

        try:
            print(f"Model: {self.cfg.llm.model}")
            print(f"Provider: {self.cfg.llm.provider}")
            print(f"Base URL: {self.cfg.llm.base_url}")

            llm = OpenAILLM(
                api_key=self.cfg.llm.api_key,
                base_url=self.cfg.llm.base_url,
                model=self.cfg.llm.model,
                default_temperature=0.0,
                default_max_tokens=100,
            )

            print("\nSending test request...")

            start_time = time.time()
            response = llm.generate(
                messages=[{"role": "user", "content": "Say 'API connection successful' in exactly those words."}],
                temperature=0.0,
                max_tokens=50,
            )
            elapsed_ms = (time.time() - start_time) * 1000

            result["latency_ms"] = round(elapsed_ms, 2)
            result["response"] = response

            if "successful" in response.lower():
                result["success"] = True
                print(f"\n✓ LLM API connection successful!")
                print(f"  Response: {response[:200]}...")
                print(f"  Latency: {result['latency_ms']}ms")
            else:
                result["error"] = f"Unexpected response: {response[:100]}"
                print(f"\n✗ LLM API returned unexpected response")
                print(f"  Response: {response[:200]}...")

        except Exception as e:
            result["error"] = str(e)
            print(f"\n✗ LLM API connection failed!")
            print(f"  Error: {e}")

        return result

    def test_embedding_api(self) -> Dict[str, Any]:
        """Test Embedding API connectivity."""
        print("\n" + "="*60)
        print("  Testing Embedding API")
        print("="*60)

        result = {
            "success": False,
            "model": self.cfg.embedding.model,
            "provider": self.cfg.embedding.provider,
            "base_url": self.cfg.embedding.base_url,
            "error": None,
            "latency_ms": None,
            "embedding_dim": None,
        }

        try:
            print(f"Model: {self.cfg.embedding.model}")
            print(f"Provider: {self.cfg.embedding.provider}")
            print(f"Base URL: {self.cfg.embedding.base_url}")

            embedder = OpenAIEmbedder(
                api_key=self.cfg.embedding.api_key,
                base_url=self.cfg.embedding.base_url,
                model=self.cfg.embedding.model,
                max_text_len=getattr(self.cfg.embedding, "max_text_len", 4096),
            )

            print("\nSending test request...")

            test_text = "This is a test sentence for embedding API."
            start_time = time.time()
            embedding = embedder.embed([test_text])
            elapsed_ms = (time.time() - start_time) * 1000

            result["latency_ms"] = round(elapsed_ms, 2)

            if embedding and len(embedding) > 0:
                result["success"] = True
                result["embedding_dim"] = len(embedding[0])
                print(f"\n✓ Embedding API connection successful!")
                print(f"  Embedding dimension: {result['embedding_dim']}")
                print(f"  Latency: {result['latency_ms']}ms")
            else:
                result["error"] = "Empty embedding returned"
                print(f"\n✗ Embedding API returned empty result")

        except Exception as e:
            result["error"] = str(e)
            print(f"\n✗ Embedding API connection failed!")
            print(f"  Error: {e}")

        return result

    def run(self) -> Dict[str, Any]:
        """Run all API tests."""
        print("\n" + "#"*60)
        print("  API Connectivity Test")
        print("#"*60)
        print(f"Config: {self.config_path}")
        print(f"LLM Model: {self.cfg.llm.model}")
        print(f"Embedding Model: {self.cfg.embedding.model}")
        print("#"*60)

        results = {
            "config": self.config_path,
            "llm": self.test_llm_api(),
            "embedding": self.test_embedding_api(),
        }

        self._print_summary(results)

        return results

    def _print_summary(self, results: Dict[str, Any]):
        """Print test summary."""
        print("\n" + "="*60)
        print("  SUMMARY")
        print("="*60)

        llm_ok = results["llm"]["success"]
        emb_ok = results["embedding"]["success"]

        print(f"LLM API:       {'✓ PASS' if llm_ok else '✗ FAIL'}")
        print(f"Embedding API: {'✓ PASS' if emb_ok else '✗ FAIL'}")

        if llm_ok and emb_ok:
            print("\n✓ All API tests passed!")
        else:
            print("\n✗ Some API tests failed")

        # Save results
        output_path = project_root / "test" / "api" / "api_test_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {output_path}")


def parse_args():
    import argparse
    p = argparse.ArgumentParser(description="Test API connectivity")
    p.add_argument(
        "--config",
        type=str,
        default=str(project_root / "configs" / "rl_bcb_config.yaml"),
        help="Path to config file (default: configs/rl_bcb_config.yaml)"
    )
    p.add_argument(
        "--llm_only",
        action="store_true",
        help="Only test LLM API"
    )
    p.add_argument(
        "--embedding_only",
        action="store_true",
        help="Only test Embedding API"
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    runner = APITestRunner(config_path=args.config)

    if args.llm_only:
        runner.test_llm_api()
    elif args.embedding_only:
        runner.test_embedding_api()
    else:
        runner.run()