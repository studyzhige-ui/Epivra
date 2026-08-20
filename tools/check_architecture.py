"""Static architecture gate: dependency direction and legacy-protocol absence.

Run this before trusting that a change kept the architecture intact::

    python tools/check_architecture.py

It exists because the failure this project is a response to was architectural,
not behavioural: a control plane that required the model to author runtime
identities produced fifteen protocol errors and zero drafts.  Tests would not
have caught that.  A layering rule does.

The gate checks three things and deliberately checks nothing else.  It does not
count lines, cap module sizes, or score complexity -- those measure effort, not
correctness, and a project converges on its right size by removing what it does
not need, not by satisfying a threshold.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "deep_research_agent"

#: Third-party packages that mark a module as infrastructure rather than domain.
INFRASTRUCTURE = frozenset(
    {"langgraph", "aiosqlite", "httpx", "aiohttp", "pypdf", "sqlite3"}
)

#: The pure domain: research meaning with no way to perform I/O.  If any of
#: these ever imports a driver, the model's vocabulary has started depending on
#: the runtime's plumbing and the two can no longer evolve separately.
DOMAIN_MODULES = frozenset({"artifacts", "contract", "sources"})

#: Layer order.  A module may import its own layer and any layer below it.
#:
#: Every module in the package must appear here.  An unlisted module used to be
#: skipped silently, which meant the gate printed "architecture OK" while never
#: checking `wave`, `reporting`, `context` or `approval` -- the orchestration
#: core.  Completeness is now enforced by :func:`check_every_module_classified`,
#: so adding a module forces a decision about where it sits.
LAYERS: tuple[tuple[str, frozenset[str]], ...] = (
    ("domain", DOMAIN_MODULES),
    (
        "trust",
        frozenset(
            {
                "approval",
                "artifact_store",
                "citations",
                "config",
                "content_store",
                "context",
                "model",
                "operations",
                "packs",
                "providers",
                "tools",
            }
        ),
    ),
    ("agents", frozenset({"agents"})),
    ("orchestration", frozenset({"reporting", "wave"})),
    ("application", frozenset({"application"})),
)

_LAYER_INDEX = {
    module: position
    for position, (_name, modules) in enumerate(LAYERS)
    for module in modules
}
_LAYER_NAME = {position: name for position, (name, _m) in enumerate(LAYERS)}

#: Symbols from the removed control plane.  Their reappearance in production
#: code means the model is being asked to author runtime control state again.
#: Each entry names the failure it caused, so a future reader can judge whether
#: a genuine exception exists rather than deleting the rule to get green.
LEGACY_SYMBOLS: tuple[tuple[str, str], ...] = (
    ("Supervisor", "model-driven routing; produced 'ended without a ready v4 decision'"),
    ("branch_id", "model-authored parallel identity; 4 of 15 recorded failures"),
    ("PublicationGateStatus", "a six-state publish machine parallel to the artifact DAG"),
    ("ResearchState", "one TypedDict holding every role's output"),
    ("AmendmentLevel", "L0/L1/L2 rework protocol"),
    ("transition_matrix", "stage routing table"),
    ("algorithm_revision", "runtime protocol versioning; reached v9"),
    ("checkpoint_adoption", "v(N-1)->v(N) checkpoint namespace migration"),
    ("role_repair", "per-role repair budget protocol"),
    ("coverage_score", "numeric sufficiency proxy standing in for judgment"),
)


@dataclass(frozen=True, slots=True)
class Violation:
    path: Path
    line: int
    message: str

    def render(self) -> str:
        return f"{self.path.relative_to(ROOT)}:{self.line}: {self.message}"


def python_files(directory: Path) -> Iterator[Path]:
    for path in sorted(directory.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def module_layer(path: Path) -> tuple[int, str] | None:
    """Return the layer position and key for a module inside the package."""

    relative = path.relative_to(PACKAGE)
    key = relative.parts[0] if len(relative.parts) > 1 else relative.stem
    position = _LAYER_INDEX.get(key)
    return None if position is None else (position, key)


def imported_names(tree: ast.AST) -> Iterator[tuple[int, str, bool]]:
    """Yield ``(line, top_level_name, is_relative)`` for every import."""

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.split(".")[0], False
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # Relative: the first component of the target module, or the
                # importing package itself for a bare "from . import x".
                name = (node.module or "").split(".")[0]
                yield node.lineno, name, True
            elif node.module:
                parts = node.module.split(".")
                if parts[0] == "deep_research_agent":
                    yield node.lineno, parts[1] if len(parts) > 1 else "", True
                else:
                    yield node.lineno, parts[0], False


def check_domain_purity(path: Path, tree: ast.AST) -> Iterator[Violation]:
    layer = module_layer(path)
    if layer is None or layer[0] != 0:
        return
    for line, name, is_relative in imported_names(tree):
        if not is_relative and name in INFRASTRUCTURE:
            yield Violation(
                path,
                line,
                f"domain module imports infrastructure {name!r}; research "
                "meaning must not depend on a driver",
            )


def check_layer_direction(path: Path, tree: ast.AST) -> Iterator[Violation]:
    layer = module_layer(path)
    if layer is None:
        return
    position, _key = layer
    for line, name, is_relative in imported_names(tree):
        if not is_relative or not name:
            continue
        target = _LAYER_INDEX.get(name)
        if target is not None and target > position:
            yield Violation(
                path,
                line,
                f"{_LAYER_NAME[position]} module imports {_LAYER_NAME[target]} "
                f"module {name!r}; dependencies point downward only",
            )


def _docstring_lines(tree: ast.Module) -> set[int]:
    """Line ranges of genuine docstrings only.

    Exempting every string constant would be far too broad: it would also
    exempt ``route = state["stage"]``, which is exactly the kind of line this
    gate exists to catch.  Only the leading string expression of a module,
    class, or function counts as documentation.
    """

    lines: set[int] = set()
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = getattr(node, "body", ())
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            end = first.end_lineno or first.lineno
            lines.update(range(first.lineno, end + 1))
    return lines


def check_legacy_symbols(path: Path, source: str) -> Iterator[Violation]:
    tree = ast.parse(source)
    # A docstring may name a removed concept in order to record that it was
    # removed, which is documentation rather than a dependency.
    exempt = _docstring_lines(tree)

    for number, text in enumerate(source.splitlines(), start=1):
        if number in exempt or text.lstrip().startswith("#"):
            continue
        for symbol, reason in LEGACY_SYMBOLS:
            if symbol in text:
                yield Violation(
                    path, number, f"legacy control-plane symbol {symbol!r} ({reason})"
                )


def check_importer_isolation() -> Iterator[Violation]:
    """One-time importers must never enter the production dependency graph."""

    tools = ROOT / "tools"
    if not tools.is_dir():
        return
    importers = {path.stem for path in tools.glob("import_*.py")}
    if not importers:
        return
    for path in python_files(PACKAGE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for line, name, _relative in imported_names(tree):
            if name in importers:
                yield Violation(
                    path,
                    line,
                    f"production code imports one-time importer {name!r}",
                )


def check_pack_boundaries() -> Iterator[Violation]:
    """Capability packs may say what to look at, never what to conclude.

    A pack that grows an evidence hierarchy, a quality rubric, a saturation
    rule, or a heading template has taken over semantic work the model owns --
    the Coverage-model failure relocated into Markdown.  The loader rejects
    those sections; this gate makes the ban visible at the repository level so a
    committed pack cannot quietly reintroduce one.
    """

    packs_root = ROOT / "packs"
    if not packs_root.is_dir():
        return
    banned = _banned_pack_sections()
    heading = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
    for path in sorted(packs_root.rglob("PACK.md")):
        for number, text in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = heading.match(text)
            if match is None:
                continue
            title = match.group(1).strip()
            reason = banned.get(title.casefold())
            if reason is not None:
                yield Violation(
                    path, number, f"barred pack section {title!r} ({reason})"
                )


def _banned_pack_sections() -> dict[str, str]:
    """Read the ban list from the package so the two cannot drift apart."""

    source = PACKAGE / "packs.py"
    if not source.is_file():
        return {}
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        target = node.target
        if not isinstance(target, ast.Name) or target.id != "BANNED_SECTIONS":
            continue
        if isinstance(node.value, ast.Dict):
            return {
                str(ast.literal_eval(key)).casefold(): str(ast.literal_eval(value))
                for key, value in zip(node.value.keys, node.value.values, strict=True)
                if key is not None
            }
    return {}


def check_every_module_classified() -> Iterator[Violation]:
    """Every package module must be placed in LAYERS.

    Without this the layer check quietly skips whatever it cannot classify, so
    the gate reports success while the newest and least-settled code is the code
    it never examined.  That is how ``wave``, ``reporting``, ``context`` and
    ``approval`` went unchecked: the list still named ``graphs`` and ``trust``
    packages that were never built, and the four real modules matched nothing.

    Failing here forces the placement decision at the moment a module is added,
    which is the only time anyone actually knows the answer.
    """

    for path in python_files(PACKAGE):
        relative = path.relative_to(PACKAGE)
        key = relative.parts[0] if len(relative.parts) > 1 else relative.stem
        if key == "__init__":
            continue
        if key not in _LAYER_INDEX:
            yield Violation(
                path,
                1,
                f"module {key!r} is not placed in any layer; add it to LAYERS so "
                "the dependency-direction check can see it",
            )


def check_readme_describes_the_current_system() -> Iterator[Violation]:
    """The README must not name a removed control-plane concept.

    It is the one document that tells a newcomer what the system *is*, and it
    drifted the furthest: it went on describing a role chain, a revision
    protocol and a CLI that had all been deleted, because it duplicated the
    architecture instead of pointing at it.  The gate never noticed because it
    only ever read ``src/``.

    Only the README is scanned.  ARCHITECTURE.md and the calibration notes have
    to be able to name what was removed and why -- recording a rejected design
    is their job.
    """

    readme = ROOT / "README.md"
    if not readme.is_file():
        return
    for number, text in enumerate(readme.read_text(encoding="utf-8").splitlines(), 1):
        for symbol, reason in LEGACY_SYMBOLS:
            if symbol in text:
                yield Violation(
                    readme,
                    number,
                    f"README names removed concept {symbol!r} ({reason}); it "
                    "should point at docs/ARCHITECTURE.md rather than restate it",
                )


def run() -> list[Violation]:
    violations: list[Violation] = []
    for path in python_files(PACKAGE):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        violations.extend(check_domain_purity(path, tree))
        violations.extend(check_layer_direction(path, tree))
        violations.extend(check_legacy_symbols(path, source))
    violations.extend(check_every_module_classified())
    violations.extend(check_readme_describes_the_current_system())
    violations.extend(check_importer_isolation())
    violations.extend(check_pack_boundaries())
    return violations


def summarise() -> Iterable[str]:
    domain = sorted(DOMAIN_MODULES)
    yield f"domain layer (no I/O): {', '.join(domain)}"
    yield f"layers, low to high: {' -> '.join(name for name, _ in LAYERS)}"
    yield f"legacy symbols barred: {len(LEGACY_SYMBOLS)}"
    yield f"pack sections barred: {len(_banned_pack_sections())}"


def main() -> int:
    violations = run()
    for line in summarise():
        print(line)
    if not violations:
        print("\narchitecture OK")
        return 0
    print(f"\n{len(violations)} violation(s):")
    for violation in violations:
        print(f"  {violation.render()}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
