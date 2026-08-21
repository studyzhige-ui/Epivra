"""Deep Research command line.

Two entry points over one service layer:

* ``deep-research`` -- the interactive workspace, for people doing research.
* ``deep-research <command>`` -- the original subcommands, for scripts, CI, MCP
  and anyone who prefers a shell.

Neither owns business logic.  Both call
:class:`deep_research_agent.service.ResearchService`, so behaviour cannot drift
between them.
"""

from __future__ import annotations

# Deliberately no re-export of ``main`` here.  Binding the function in the
# package namespace shadows the ``cli.main`` *module*, so ``from
# deep_research_agent.cli import main`` would hand a caller the function while
# they expected the module -- a confusion that cost a round of failing tests.
# The console script names the module path instead.

__all__: list[str] = []
