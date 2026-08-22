"""Deep Research command line.

``deep-research`` opens the interactive workspace: the interface a person uses.
``deep-research doctor`` reports on the environment, which is a different job --
finding out why the product will not run rather than running it.

Nothing here owns business logic.  The workspace calls
:class:`deep_research_agent.service.ResearchService` directly, and any other
front end is expected to do the same, so behaviour cannot drift between them.
"""

from __future__ import annotations

# Deliberately no re-export of ``main`` here.  Binding the function in the
# package namespace shadows the ``cli.main`` *module*, so ``from
# deep_research_agent.cli import main`` would hand a caller the function while
# they expected the module -- a confusion that cost a round of failing tests.
# The console script names the module path instead.

__all__: list[str] = []
