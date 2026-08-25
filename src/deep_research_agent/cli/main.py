"""Entry point and dispatch.

The surface is two things:

* ``deep-research`` -- the interactive workspace.  This is the product, and the
  only interface a person needs in order to do research.
* ``deep-research doctor`` -- diagnostics.  A different job from using the
  product: one shot, no navigation, output meant to be read or pasted.

Plus ``--help`` and ``--version``, which are what every command-line tool owes
its user.

Without a terminal there is no workspace to enter, so a bare invocation prints
help and exits successfully rather than blocking on a prompt nobody can answer.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .. import __version__
from . import doctor, theme
from .paths import default_database

DESCRIPTION = """\
Deep Research

直接运行 deep-research 进入交互式研究工作区。

commands:
  doctor       检查 Deep Research 环境与服务连接\
"""


def build_parser() -> argparse.ArgumentParser:
    """The whole public surface, in one place.

    argparse prints a lone command twice -- once as the group's metavar and once
    as the choice -- so the command list lives in the description and the
    subparser group is suppressed from help.  A test asserts every registered
    command appears in that text, so the two cannot drift apart.
    """

    parser = argparse.ArgumentParser(
        prog="deep-research",
        usage="deep-research [options] [doctor]",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="显示帮助 / show this help",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"deep-research {__version__}",
        help="显示版本 / show the version",
    )
    parser.add_argument(
        "--database", default="", help="任务库路径 / path to the task database"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志 / show the detailed provider log",
    )
    sub = parser.add_subparsers(dest="command", help=argparse.SUPPRESS)

    diagnose = sub.add_parser("doctor", help=argparse.SUPPRESS)
    diagnose.add_argument(
        "--live",
        action="store_true",
        help="真的调用每个已配置厂商一次 / call every configured provider once",
    )
    diagnose.set_defaults(run=doctor.run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.database:
        args.database = str(default_database())

    if args.command is None:
        if not theme.is_interactive():
            # No terminal means no workspace to enter.  Help and a success exit,
            # never a prompt that will not be answered.  Machine callers use the
            # Python API directly.
            parser.print_help()
            return 0
        from .workspace import run_workspace

        return run_workspace(args)

    return asyncio.run(args.run(args))


if __name__ == "__main__":  # pragma: no cover - console script entry
    sys.exit(main())
