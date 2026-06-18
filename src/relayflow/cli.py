"""RelayFlow command-line entry point.

Subcommands:

* ``run``     — run the demo task once (relay on by default), persisting sessions.
* ``matrix``  — run the three-cell falsification matrix and report the verdict.
* ``inspect`` — replay a persisted session's recorded I/O trace (no model call).
"""

from __future__ import annotations

import argparse
import os
import sys

from relayflow import __version__
from relayflow.artifact import ArtifactStore
from relayflow.demo import MarkerRelayTask, build_marker_graph, marker_responder
from relayflow.falsification import run_experiment_matrix, run_task
from relayflow.firewall import Budget
from relayflow.graph import run_graph, visualize
from relayflow.llm import MockLLM
from relayflow.session import SessionNotFound, SessionStore

DEFAULT_DB = ".relayflow/relayflow.db"


def _ensure_parent(path: str) -> None:
    if path == ":memory:":
        return
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="relayflow")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run the demo task once")
    run.add_argument("--db", default=DEFAULT_DB)
    run.add_argument("--budget", type=int, default=60)
    run.add_argument(
        "--no-relay", action="store_true", help="degenerate single session"
    )
    run.set_defaults(func=cmd_run)

    matrix = sub.add_parser("matrix", help="run the falsification matrix")
    matrix.add_argument("--budget", type=int, default=60)
    matrix.set_defaults(func=cmd_matrix)

    inspect = sub.add_parser("inspect", help="replay a persisted session trace")
    inspect.add_argument("session_id")
    inspect.add_argument("--db", default=DEFAULT_DB)
    inspect.set_defaults(func=cmd_inspect)

    graph = sub.add_parser("graph", help="run the demo session graph and visualize")
    graph.add_argument("--budget", type=int, default=60)
    graph.set_defaults(func=cmd_graph)

    return parser


def cmd_run(args: argparse.Namespace) -> int:
    _ensure_parent(args.db)
    task = MarkerRelayTask()
    artifacts = ArtifactStore(args.db)
    task.setup(artifacts)
    sessions = SessionStore(args.db)
    report = run_task(
        artifacts,
        MockLLM(responder=marker_responder),
        task,
        relay=not args.no_relay,
        budget=Budget(max_tokens=args.budget),
        sessions=sessions,
    )
    print(f"mode={report.mode} budget={report.budget} sessions={report.sessions}")
    print(f"peak_session_tokens={report.peak_session_tokens}")
    print(f"acceptance={report.acceptance}")
    return 0


def cmd_matrix(args: argparse.Namespace) -> int:
    matrix = run_experiment_matrix(
        MarkerRelayTask(), MockLLM(responder=marker_responder), args.budget
    )
    print(f"budget={matrix.budget} single_shot_tokens={matrix.single_shot_tokens}")
    for label, cell in (
        ("relay-off/unbounded", matrix.relay_off_unbounded),
        ("relay-off/bounded  ", matrix.relay_off_bounded),
        ("relay-on /bounded  ", matrix.relay_on_bounded),
    ):
        print(
            f"  {label}  sessions={cell.sessions} "
            f"peak={cell.peak_session_tokens} -> {cell.acceptance}"
        )
    print(f"bet_holds={matrix.bet_holds}")
    return 0 if matrix.bet_holds else 1


def cmd_inspect(args: argparse.Namespace) -> int:
    sessions = SessionStore(args.db)
    try:
        record = sessions.get(args.session_id)
    except SessionNotFound:
        print(f"session not found: {args.session_id}", file=sys.stderr)
        return 1
    print(f"session: {record.id}")
    print(f"purpose: {record.input.get('purpose')}")
    print(f"summary: {record.output.get('summary')}")
    print("artifacts:")
    for ref in record.artifacts:
        print(f"  - {ref}")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    task = MarkerRelayTask()
    artifacts = ArtifactStore()
    task.setup(artifacts)
    graph = build_marker_graph(task, Budget(max_tokens=args.budget))
    result = run_graph(graph, artifacts, MockLLM(responder=marker_responder))
    print(visualize(graph))
    print(f"completed={result.completed}")
    if result.failed:
        print(f"failed={result.failed}")
    if result.blocked:
        print(f"blocked={result.blocked}")
    return 0 if not result.failed and not result.blocked else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command", None) is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
