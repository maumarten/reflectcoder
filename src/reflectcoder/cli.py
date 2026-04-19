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

    args = parser.parse_args(argv)
    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")

    if args.cmd == "eval":
        return _cmd_eval(args, settings)

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
    if args.agent == "reflective":
        agent_kwargs["max_iter"] = args.max_iter
    agent = agent_cls(**agent_kwargs)

    report = run_eval(agent, tasks, settings.run_dir)
    return 0 if report.pass_rate == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
