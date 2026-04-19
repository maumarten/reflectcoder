from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table

from reflectcoder.agents.base import Agent
from reflectcoder.schemas import EvalReport, RunResult, Task

log = logging.getLogger(__name__)
console = Console()


def load_fixtures(fixtures_dir: Path, only: list[str] | None = None) -> list[Task]:
    """Load all fixture tasks from disk, sorted by task_id for reproducibility."""
    tasks: list[Task] = []
    for task_json in sorted(fixtures_dir.glob("*/task.json")):
        task_dir = task_json.parent
        data = json.loads(task_json.read_text(encoding="utf-8"))

        source_files = _load_tree(task_dir / "source", data["source_files"])
        test_files = _load_tree(task_dir / "tests", data["test_files"])

        task = Task(
            task_id=data["task_id"],
            title=data["title"],
            problem=data["problem"],
            source_files=source_files,
            test_files=test_files,
            tags=data.get("tags", []),
            difficulty=data.get("difficulty", "easy"),
        )
        if only and task.task_id not in only:
            continue
        tasks.append(task)
    return tasks


def _load_tree(root: Path, rel_paths: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in rel_paths:
        path = root / rel
        out[rel] = path.read_text(encoding="utf-8")
    return out


def run_eval(agent: Agent, tasks: list[Task], run_dir: Path) -> EvalReport:
    """Run an agent against every task and emit a report.

    Deterministic output: results are sorted by task_id, and every run gets a
    timestamped directory under `run_dir` containing the full report JSON.
    """
    results: list[RunResult] = []
    console.rule(f"[bold]Eval: agent={agent.name}, n_tasks={len(tasks)}")

    for task in tasks:
        console.print(f"[dim]>[/dim] {task.task_id}  [cyan]{task.title}[/cyan]")
        started = time.monotonic()
        try:
            result = agent.solve(task)
        except Exception as e:
            result = RunResult(
                task_id=task.task_id,
                agent=agent.name,
                model=getattr(agent, "model", "unknown"),
                passed=False,
                wall_clock_s=time.monotonic() - started,
                error=f"agent_crash: {type(e).__name__}: {e}",
            )
        _print_result(result)
        results.append(result)

    report = _build_report(agent, results, run_dir)
    _print_summary(report)
    _persist_report(report, run_dir)
    return report


def _print_result(result: RunResult) -> None:
    status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
    extra = f"[dim] {result.total_tokens} tok  {result.wall_clock_s:.1f}s[/dim]"
    console.print(f"    {status}{extra}")
    if result.error:
        console.print(f"    [red]{result.error}[/red]")


def _build_report(agent: Agent, results: list[RunResult], run_dir: Path) -> EvalReport:
    n_passed = sum(1 for r in results if r.passed)
    model = results[0].model if results else getattr(agent, "model", "unknown")
    return EvalReport(
        agent=agent.name,
        model=model,
        n_tasks=len(results),
        n_passed=n_passed,
        pass_rate=(n_passed / len(results)) if results else 0.0,
        total_tokens=sum(r.total_tokens for r in results),
        total_wall_clock_s=sum(r.wall_clock_s for r in results),
        results=results,
        run_dir=run_dir,
    )


def _print_summary(report: EvalReport) -> None:
    table = Table(title=f"Eval summary — {report.agent} / {report.model}")
    table.add_column("metric", style="cyan")
    table.add_column("value", style="bold")
    table.add_row("tasks", str(report.n_tasks))
    table.add_row("passed", str(report.n_passed))
    table.add_row("pass rate", f"{report.pass_rate:.1%}")
    table.add_row("total tokens", str(report.total_tokens))
    table.add_row("wall clock", f"{report.total_wall_clock_s:.1f}s")
    console.print(table)


def _persist_report(report: EvalReport, run_dir: Path) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = run_dir / f"{stamp}_{report.agent}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        report.model_dump_json(indent=2, exclude={"run_dir"}),
        encoding="utf-8",
    )
    console.print(f"[dim]report written to {out_dir / 'report.json'}[/dim]")
