"""Citation identity and rendering; support for a claim remains a research judgment."""

import re
from urllib.parse import urlsplit

from markdown_it import MarkdownIt

MARKER = re.compile(r"\[\[cite:([0-9a-f]{64})\]\]")
NUMBER = re.compile(r"\[(\d+)\]")


def prose(text):
    """Mask CommonMark code blocks and code spans without changing offsets."""
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    chars = list(text)
    for token in MarkdownIt().parse(text):
        if token.map is None:
            continue
        start, stop = (offsets[n] for n in token.map)
        if token.type in {"fence", "code_block"}:
            chars[start:stop] = " " * (stop - start)
        elif token.type == "inline":
            block = text[start:stop]
            runs = list(re.finditer(r"(?<!`)`+(?!`)", block))
            cursor = 0
            for index, run in enumerate(runs):
                if run.start() < cursor:
                    continue
                prefix = block[: run.start()]
                if (len(prefix) - len(prefix.rstrip("\\"))) % 2:
                    continue
                end = next(
                    (r for r in runs[index + 1 :] if len(r[0]) == len(run[0])), None
                )
                if end:
                    chars[start + run.start() : start + end.end()] = " " * (
                        end.end() - run.start()
                    )
                    cursor = end.end()
    return re.sub(r"\\.", "  ", "".join(chars))


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
    visible = prose(text)
    matches = list(MARKER.finditer(visible))
    remainder = MARKER.sub("", visible)
    if re.search(
        r"\[\[\s*cite\b|\[\d+(?:\s*[,–-]\s*\d+)*\]", remainder, re.I
    ):
        raise ValueError(
            "Use [[cite:<full source or evidence-note ref>]], not manual citation numbers"
        )
    refs = [m[1] for m in matches]
    if refs and any(
        token.type == "fence"
        and token.map[1] - token.map[0] <= len(token.content.splitlines()) + 1
        for token in MarkdownIt().parse(text)
    ):
        raise ValueError("Close the fenced code block before adding the bibliography")
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
        label = re.sub(
            r"([\\`*{}\[\]<>_])", r"\\\1", origin.replace("\n", " ").replace("\r", " ")
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
    return {
        "text": body + ("\n\n---\n\n" + "\n\n".join(footer) if footer else ""),
        "citations": refs,
        "citation_body_length": len(body),
    }


def validate(report, resolve):
    """Reconstruct markers without a duplicate manuscript and compare exact output."""
    text = report["text"]
    refs = report.get("citations", [])
    length = report.get("citation_body_length", len(text))
    if type(length) is not int or not 0 <= length <= len(text):
        raise ValueError("invalid citation body boundary")
    body = text[:length]
    matches = list(NUMBER.finditer(prose(body)))
    parts, end = [], 0
    if len(matches) != len(refs):
        raise ValueError("citation occurrence binding has changed")
    for index, m in enumerate(matches):
        if int(m[1]) < 1:
            raise ValueError("unknown rendered citation")
        parts.extend((body[end : m.start()], "[[cite:" + refs[index] + "]]"))
        end = m.end()
    parts.append(body[end:])
    expected = render("".join(parts), report["evidence"], resolve)
    if expected != {"text": text, "citations": refs, "citation_body_length": length}:
        raise ValueError("report citation rendering or binding has changed")
