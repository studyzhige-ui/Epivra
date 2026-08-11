"""Thin CLI over the same durable Python API."""

from __future__ import annotations

import argparse
import asyncio
import importlib
from pathlib import Path
from typing import Any

from . import __version__
from .api import (
    DEFAULT_WORKFLOW_RECURSION_LIMIT,
    RunResult,
    inspect_sqlite_task,
    open_sqlite_agent,
)
from .roles import RoleExecutors
from .runtime import build_environment_runtime


def _load_roles(spec: str) -> RoleExecutors:
    if ":" not in spec:
        raise ValueError("--roles must use module:attribute syntax")
    module_name, attribute_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    value: Any = getattr(module, attribute_name)
    if isinstance(value, type):
        value = value()
    elif callable(value) and not isinstance(value, RoleExecutors):
        value = value()
    if not isinstance(value, RoleExecutors):
        raise TypeError("loaded object must be a RoleExecutors instance")
    return value


def _print_result(result: RunResult) -> None:
    if result.status == "awaiting_approval":
        print(result.approval_card)
        print(
            f"\n任务 {result.task_id} 正在等待人工确认。"
            "请用 resume --approve、--revise 或 --cancel 继续。"
        )
    elif result.status == "awaiting_user":
        print(result.user_prompt)
        print(f"\n任务 {result.task_id} 正在等待用户回答。")
    elif result.status == "completed":
        print(result.final_report)
    elif result.status == "retryable_failure":
        print(result.error_summary)
        print(f"\n任务 {result.task_id} 可使用 retry 显式重试失败步骤。")
    elif result.status == "recoverable_pause":
        print(result.error_summary)
        print(f"\n任务 {result.task_id} 可使用 continue 继续未完成步骤。")
    elif result.status == "cancelled":
        print(f"任务 {result.task_id} 已取消。")
    else:
        print(f"任务 {result.task_id} 已暂停，当前没有可展示的用户决策。")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deep-research-agent")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="验证本地核心安装")
    doctor.set_defaults(command="doctor")

    def runtime_arguments(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--roles",
            help=(
                "RoleExecutors 的 module:attribute；会以当前进程权限执行，"
                "只能加载用户明确信任的本地代码。省略时使用内置 DeepSeek + "
                "已配置搜索运行时"
            ),
        )
        subparser.add_argument(
            "--guides",
            type=Path,
            help=(
                "自定义 Domain/Capability Guide 根目录；省略时使用随项目安装的"
                "内置 Guides"
            ),
        )
        subparser.add_argument(
            "--database",
            type=Path,
            default=Path(".deep-research-agent/checkpoints.sqlite3"),
            help="SQLite Checkpoint 文件",
        )
        subparser.add_argument(
            "--recursion-limit",
            type=int,
            default=DEFAULT_WORKFLOW_RECURSION_LIMIT,
            help=(
                "父图单次调用的技术递归保护上限；仅防失控循环，"
                "不表示研究预算或停止条件"
            ),
        )

    run = subparsers.add_parser("run", help="创建研究任务并生成审批卡")
    runtime_arguments(run)
    run.add_argument("question")
    run.add_argument("--thread-id")

    resume = subparsers.add_parser("resume", help="恢复等待中的任务")
    runtime_arguments(resume)
    resume.add_argument("thread_id")
    choice = resume.add_mutually_exclusive_group(required=True)
    choice.add_argument("--approve", action="store_true")
    choice.add_argument("--revise", metavar="FEEDBACK")
    choice.add_argument("--cancel", action="store_true")
    choice.add_argument("--response", metavar="TEXT")

    retry = subparsers.add_parser("retry", help="重试已保存的失败步骤")
    runtime_arguments(retry)
    retry.add_argument("thread_id")

    continue_parser = subparsers.add_parser(
        "continue", help="继续无错误、无人工中断但仍有待执行步骤的任务"
    )
    runtime_arguments(continue_parser)
    continue_parser.add_argument("thread_id")

    status = subparsers.add_parser("status", help="查看任务的用户可见状态")
    status.add_argument("thread_id")
    status.add_argument(
        "--database",
        type=Path,
        default=Path(".deep-research-agent/checkpoints.sqlite3"),
        help="SQLite Checkpoint 文件",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    if args.command == "doctor":
        print(
            "Deep Research Agent 核心已安装：LangGraph、SQLite Checkpoint、"
            "八角色契约和引用编译器可用。未调用任何模型或搜索 API。"
        )
        return 0

    if args.command == "status":
        result = await inspect_sqlite_task(args.database, args.thread_id)
        _print_result(result)
        return _exit_code(result)

    if args.roles:
        roles = _load_roles(args.roles)
        runtime_options: dict[str, Any] = {}
    else:
        runtime = build_environment_runtime(guide_root=args.guides)
        roles = runtime.roles
        runtime_options = {
            "guide_context": runtime.guide_context,
            "guide_catalog": runtime.guide_catalog,
        }
    async with open_sqlite_agent(
        roles,
        args.database,
        recursion_limit=args.recursion_limit,
        **runtime_options,
    ) as agent:
        if args.command == "run":
            result = await agent.start(args.question, task_id=args.thread_id)
        elif args.command == "retry":
            result = await agent.retry(args.thread_id)
        elif args.command == "continue":
            result = await agent.continue_task(args.thread_id)
        else:
            if args.approve:
                response: Any = {"action": "approve"}
            elif args.cancel:
                response = {"action": "cancel"}
            elif args.revise is not None:
                response = {"action": "revise", "feedback": args.revise}
            else:
                response = {"response": args.response}
            result = await agent.resume(args.thread_id, response)
    _print_result(result)
    return _exit_code(result)


def _exit_code(result: RunResult) -> int:
    if result.status in {"retryable_failure", "recoverable_pause", "paused"}:
        return 2
    return 0


def main() -> int:
    args = _parser().parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
