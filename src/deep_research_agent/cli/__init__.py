"""Deep Research command line.

One human-facing interface: ``deep-research`` opens the interactive workspace.
``deep-research doctor`` diagnoses the environment, which is a different job from
using the product.

There used to be a second: the whole research workflow as subcommands.  Two
human interfaces over one service meant every feature was built, translated and
tested twice, and the command path always lagged behind.  Machine access is a
real need and it is not served well by a shell wrapper -- that is MCP's job, over
the same :class:`deep_research_agent.service.ResearchService` the workspace uses.

Nothing here owns business logic.  Both the workspace and any future MCP server
call the service directly, so behaviour cannot drift between them.
"""

from __future__ import annotations

# Deliberately no re-export of ``main`` here.  Binding the function in the
# package namespace shadows the ``cli.main`` *module*, so ``from
# deep_research_agent.cli import main`` would hand a caller the function while
# they expected the module -- a confusion that cost a round of failing tests.
# The console script names the module path instead.

__all__: list[str] = []
