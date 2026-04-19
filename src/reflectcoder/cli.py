from __future__ import annotations

import argparse
import logging
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from reflectcoder.agents import AGENT_REGISTRY
from reflectcoder.config import FIXTURES_DIR, Settings
from reflectcoder.evals.harness import load_fixtures, run_eval
from reflectcoder.llm import LLMClient
from reflectcoder.memory import FailureMemory, default_embedder
from reflectcoder.sandbox import SubprocessSandbox


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reflectcoder")
    sub = parser.add_subparsers(dest="cmd", required=True)

    eval_p = sub.add_parser("eval", help="Run an agent against the fixture set")
    eval_p.add_argument("--agent", default="stub", choices=sorted(AGENT_REGISTRY.keys()))
    eval_p.add_argument(
        "--task",
        action="append",
        default=None,
        help="Only run this task_id (repeatable)",
    )
    eval_p.add_argument("--timeout", type=float, default=20.0, help="Per-task sandbox timeout")
    eval_p.add_argument(
        "--max-iter",
        type=int,
        default=3,
        help="Max iterations for iterative agents (reflective, etc.)",
    )
    eval_p.add_argument(
        "--memory-path",
        default=None,
        help="Override path to the failure memory SQLite store (reflective-memory).",
    )
    eval_p.add_argument(
        "--reset-memory",
        action="store_true",
        help="Wipe the failure memory store before running (reflective-memory).",
    )
    eval_p.add_argument(
        "--retrieval-k",
        type=int,
        default=3,
        help="Top-k prior failures to retrieve per proposer call (reflective-memory).",
    )

    mem_p = sub.add_parser("memory", help="Inspect the failure memory store")
    mem_p.add_argument("--memory-path", default=None)
    mem_p.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(argv)
    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")

    if args.cmd == "eval":
        return _cmd_eval(args, settings)
    if args.cmd == "memory":
        return _cmd_memory(args, settings)

    parser.print_help()
    return 1


def _cmd_eval(args: argparse.Namespace, settings: Settings) -> int:
    tasks = load_fixtures(FIXTURES_DIR, only=args.task)
    if not tasks:
        print("No fixtures matched. Check src/reflectcoder/evals/fixtures/.", file=sys.stderr)
        return 2

    llm = LLMClient(api_key=settings.groq_api_key, model=settings.model)
    sandbox = SubprocessSandbox(timeout_s=args.timeout)
    agent_cls = AGENT_REGISTRY[args.agent]
    agent_kwargs: dict = {"llm": llm, "sandbox": sandbox}
    memory: FailureMemory | None = None
    try:
        if args.agent in ("reflective", "reflective-memory"):
            agent_kwargs["max_iter"] = args.max_iter
        if args.agent == "reflective-memory":
            from pathlib import Path

            memory_path = Path(args.memory_path) if args.memory_path else settings.memory_path
            memory = FailureMemory(memory_path, embedder=default_embedder())
            if args.reset_memory:
                memory.clear()
            print(
                f"[memory] {memory.path} embedder={memory.embedder_name} "
                f"rows_before_run={memory.count()}",
                file=sys.stderr,
            )
            agent_kwargs["memory"] = memory
            agent_kwargs["retrieval_k"] = args.retrieval_k
        agent = agent_cls(**agent_kwargs)

        report = run_eval(agent, tasks, settings.run_dir)

        if memory is not None:
            print(
                f"[memory] rows_after_run={memory.count()}",
                file=sys.stderr,
            )
        return 0 if report.pass_rate == 1.0 else 1
    finally:
        if memory is not None:
            memory.close()


def _cmd_memory(args: argparse.Namespace, settings: Settings) -> int:
    from pathlib import Path

    memory_path = Path(args.memory_path) if args.memory_path else settings.memory_path
    if not memory_path.exists():
        print(f"No memory store at {memory_path}", file=sys.stderr)
        return 0
    memory = FailureMemory(memory_path, embedder=default_embedder())
    try:
        print(f"store: {memory.path}")
        print(f"rows:  {memory.count()}")
        recent = memory.dump_recent(args.limit)
        for row in recent:
            snippet = row["reflection"]
            if len(snippet) > 160:
                snippet = snippet[:160] + "..."
            print(f"  [{row['id']}] {row['task_id']} @ {row['created_at']}  {snippet}")
    finally:
        memory.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
