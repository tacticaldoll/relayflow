"""RelayFlow command-line entry point.

Subcommands are wired in as the runtime is built. For now this exposes
``--version``; ``inspect`` and the experiment-matrix runner are added in later
task groups.
"""

from __future__ import annotations

import argparse

from relayflow import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="relayflow")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_subparsers(dest="command")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command", None) is None:
        parser.print_help()
        return 0
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
