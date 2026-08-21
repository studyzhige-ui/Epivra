"""Entry point and dispatch.

The rule this module exists to enforce:

* ``deep-research`` with no command, on a terminal, **enters the workspace**.
  The product is a place you work, not a set of commands you remember.
* ``deep-research <command>`` keeps working exactly as before, so scripts, CI and
  MCP are unaffected.
* ``deep-research`` with no command and **no terminal** prints help instead of
  blocking on a prompt that will never be answered.

``--help`` owns the command list now.  A bare invocation used to print a welcome
screen plus every command; that made the front door a menu rather than a place to
start.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from . import commands, theme
from .paths import default_database, settings_file
from .settings import load as load_settings

USAGE = """\
Usage:
  deep-research
  deep-research <command> [options]

Without a command, starts the interactive Deep Research workspace.

Commands:
  new        Start a new research
  list       List research tasks
  show       Show research details
  approve    Approve a research plan
  continue   Continue a paused research
  report     Read or export a report
  delete     Delete a research and everything it produced
  init       Configure providers
  doctor     Check the environment
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deep-research",
        usage=USAGE,
        description="Deep Research — research you can trace back to the evidence.",
        add_help=True,
    )
    parser.add_argument("--database", default="", help="任务库路径 / database path")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志 / show the detailed provider log",
    )
    sub = parser.add_subparsers(dest="command")

    new = sub.add_parser("new", help="Start a new research")
    new.add_argument("request", nargs="?", default="")
    new.add_argument("--corpus", default="")
    new.set_defaults(run=commands.cmd_new)

    init = sub.add_parser("init", help="Configure providers")
    init.add_argument("--config", default="")
    init.add_argument("--force", action="store_true")
    init.set_defaults(run=commands.cmd_init)

    doctor = sub.add_parser("doctor", help="Check the environment")
    doctor.add_argument(
        "--live",
        action="store_true",
        help="重新验证每个已配置厂商 / re-validate every configured provider",
    )
    doctor.set_defaults(run=commands.cmd_doctor)

    listing = sub.add_parser("list", help="List research tasks")
    listing.set_defaults(run=commands.cmd_list)

    show = sub.add_parser("show", help="Show research details")
    show.add_argument("task_id")
    show.set_defaults(run=commands.cmd_show)

    approve = sub.add_parser("approve", help="Approve a research plan")
    approve.add_argument("task_id")
    approve.add_argument("--note", default="")
    approve.add_argument("--corpus", default="")
    approve.add_argument("--no-run", action="store_true")
    approve.set_defaults(run=commands.cmd_approve)

    resume = sub.add_parser("continue", help="Continue a paused research")
    resume.add_argument("task_id")
    resume.add_argument("--corpus", default="")
    resume.set_defaults(run=commands.cmd_continue)

    report = sub.add_parser("report", help="Read or export a report")
    report.add_argument("task_id")
    report.add_argument("-o", "--output", default="")
    report.set_defaults(run=commands.cmd_report)

    delete = sub.add_parser(
        "delete", help="Delete a research and everything it produced"
    )
    delete.add_argument("task_id")
    delete.add_argument(
        "--yes", action="store_true", help="跳过确认 / skip the confirmation"
    )
    delete.set_defaults(run=commands.cmd_delete)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.database:
        args.database = str(default_database())

    if args.command is None:
        if not theme.is_interactive():
            # A pipe or a redirect gets help, never a prompt: blocking forever on
            # stdin that no human will type into is the worst failure available.
            settings = load_settings(settings_file())
            from .i18n import Translator

            print(Translator(settings.language)("generic.needs_tty"))
            print()
            print(USAGE)
            return 0
        from .workspace import run_workspace

        return run_workspace(args)

    try:
        return asyncio.run(args.run(args))
    except KeyboardInterrupt:
        # Command mode is scriptable, so an interrupt reports and exits rather
        # than offering a menu; the artifacts are already durable either way.
        print()
        settings = load_settings(settings_file())
        from .i18n import Translator

        print(Translator(settings.language)("interrupt.on_exit"))
        return 130
    except ValueError as error:
        print(f"\n{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
