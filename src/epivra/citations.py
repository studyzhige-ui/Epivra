"""Citation identity and rendering; support for a claim remains a research judgment."""

import re
from urllib.parse import urlsplit

from markdown_it import MarkdownIt

MARKER = re.compile(r"\[\[cite:([0-9a-f]{64})\]\]")
NUMBER = re.compile(r"\[(\d+)\]")


def source_lines(text):
    """CommonMark CRLF/CR/LF boundaries, retaining original character offsets."""
    return re.findall(r"[^\r\n]*(?:\r\n|\r|\n|$)", text)[:-1]


def occurrences(text, numbered=False):
    """Recognize citations through inline grammar; map only recognized markers back.

    Container prefixes cannot contain citation markers. Counting identical markers
    on the original line preserves offsets even when CommonMark strips prefixes.
    No Markdown is regenerated and no independent code-span parser is used.
    """
    lines = source_lines(text)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    found = []
    active = None
    active_line = 0
    prior = {}
    pattern = NUMBER if numbered else MARKER
    parser = MarkdownIt("default", {"html": False})

    def citation(state, silent):
        if active is None or state.src != active.content:
            return False  # Image attributes use a separate nested inline source.
        match = pattern.match(state.src, state.pos)
        if match is None:
            if re.match(
                r"\[\[\s*cite\b|\[\d+(?:\s*[,–-]\s*\d+)*\]",
                state.src[state.pos :],
                re.I,
            ):
                if not silent:
                    raise ValueError(
                        "Use [[cite:<full source or evidence-note ref>]], not manual citation numbers"
                    )
            return False
        if not silent:
            before = state.src[: state.pos]
            relative_line = before.count("\n")
            line = active_line + relative_line
            start = before.rfind("\n") + 1
            ordinal = prior.get((line, match[0]), 0) + state.src[
                start : state.pos
            ].count(match[0])
            position = -1
            for _ in range(ordinal + 1):
                position = lines[line].find(match[0], position + 1)
                if position < 0:
                    raise ValueError("citation source position cannot be resolved")
            original = pattern.match(text, offsets[line] + position)
            found.append(original)
            token = state.push("text", "", 0)
            token.content = match[0]
        state.pos = match.end()
        return True

    def inline(state):
        nonlocal active, active_line
        block_line = 0
        for token in state.tokens:
            if token.map is not None:
                block_line = token.map[0]
            if token.type == "inline":
                active = token
                active_line = block_line
                token.children = []
                state.md.inline.parse(
                    token.content, state.md, state.env, token.children
                )
                # Cells share a row: count raw occurrences in earlier cells,
                # including literals in code/URLs, to preserve original offsets.
                for match in pattern.finditer(token.content):
                    line = active_line + token.content[: match.start()].count("\n")
                    key = (line, match[0])
                    prior[key] = prior.get(key, 0) + 1
        active = None

    parser.inline.ruler.before("link", "epivra_citation", citation)
    parser.core.ruler.at("inline", inline)
    env = {}
    parser.parse(text, env)
    if any(re.fullmatch(r"\d+", key) for key in env.get("references", {})):
        raise ValueError(
            "Numeric reference definitions conflict with generated citations"
        )
    return sorted(found, key=lambda m: m.start())


def render(text, evidence, resolve):
    lookup = resolve

    def resolve(ref):
        try:
            return lookup(ref)
        except (KeyError, ValueError) as exc:
            raise ValueError("unknown citation/source reference: " + str(ref)) from exc

    sources = {ref: resolve(ref) for ref in evidence}
    if any(s.kind != "source" for s in sources.values()):
        raise ValueError("report evidence must name source snapshots")
    matches = occurrences(text)
    refs = [m[1] for m in matches]
    targets = []
    for ref in refs:
        item = resolve(ref)
        source = item
        if item.kind == "note":
            source = resolve(item.body.get("source", ""))
            quote, offset = item.body.get("quote"), item.body.get("offset")
            if (
                not isinstance(quote, str)
                or not quote.strip()
                or type(offset) is not int
                or offset < 0
                or source.ref not in item.parents
                or source.body.get("text", "")[offset : offset + len(quote)] != quote
            ):
                raise ValueError("citation note must bind an exact original passage")
        if source.kind != "source" or source.ref not in sources:
            raise ValueError("citation must resolve to a source in report evidence")
        targets.append(source)
    unique = list({source.ref: source for source in targets}.values())
    numbers = {source.ref: i + 1 for i, source in enumerate(unique)}
    result, end = [], 0
    for match, source in zip(matches, targets):
        result.extend((text[end : match.start()], f"[{numbers[source.ref]}]"))
        end = match.end()
    result.append(text[end:])
    body = "".join(result)
    footer = []
    for number, source in enumerate(unique, 1):
        origin = str(source.body.get("origin") or f"Source {number}")
        title = source.body.get("title") or source.body.get("name") or origin
        if not isinstance(title, str):
            title = origin
        label = re.sub(
            r"([\\`*{}\[\]<>_])", r"\\\1", title.replace("\n", " ").replace("\r", " ")
        )
        if urlsplit(origin).scheme in {"http", "https"}:
            url = (
                origin.replace("<", "%3C")
                .replace(">", "%3E")
                .replace("\n", "%0A")
                .replace("\r", "%0D")
            )
            label = f"[{label}](<{url}>)"
        footer.append(f"{number}. {label}")
    rendered = body + ("\n\n---\n\n" + "\n\n".join(footer) if footer else "")
    if footer:
        # Validate the actual appended list, including implicit container endings.
        start_line = len(source_lines(body + "\n\n---\n\n"))
        if not any(
            t.type == "ordered_list_open" and t.level == 0 and t.map[0] == start_line
            for t in MarkdownIt("default", {"html": False}).parse(rendered)
        ):
            raise ValueError(
                "Close the fenced code block or container before adding the bibliography"
            )
    return {
        "text": rendered,
        "citations": refs,
        "citation_body_length": len(body),
    }


def manuscript(report, resolve):
    """Return editable citation markers only after the saved rendering roundtrips."""
    text = report["text"]
    refs = report.get("citations", [])
    length = report.get("citation_body_length", len(text))
    if type(length) is not int or not 0 <= length <= len(text):
        raise ValueError("invalid citation body boundary")
    body = text[:length]
    matches = occurrences(body, numbered=True)
    parts, end = [], 0
    if len(matches) != len(refs):
        raise ValueError("citation occurrence binding has changed")
    for index, m in enumerate(matches):
        if int(m[1]) < 1:
            raise ValueError("unknown rendered citation")
        parts.extend((body[end : m.start()], "[[cite:" + refs[index] + "]]"))
        end = m.end()
    parts.append(body[end:])
    original = "".join(parts)
    expected = render(original, report["evidence"], resolve)
    if expected != {"text": text, "citations": refs, "citation_body_length": length}:
        raise ValueError("report citation rendering or binding has changed")
    return original


def validate(report, resolve):
    """Validate exact citation identity with the shared reconstruction contract."""
    manuscript(report, resolve)
