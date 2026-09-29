"""Lossless source windows and deterministic, rebuildable passage indexes."""

import re
from collections import Counter
from math import log1p

from markdown_it import MarkdownIt

CHUNK_CHARACTERS = 2400  # Local retrieval granularity, not a provider token limit.
INDEX_VERSION = "passages-bm25-v5"


def window(source, start, end):
    text = source.body["text"]
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(text):
        raise ValueError("invalid original source window")
    return {
        "ref": source.ref, "kind": "source", "offset": start, "end": end,
        "total": len(text), "next_offset": end if end < len(text) else None,
        "text": text[start:end],
        "selections": [
            {"selection": f"{source.ref}:{start + m.start()}:{start + m.end()}",
             "preview": m.group()[:100]}
            for m in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", text[start:end])
        ],
        **{key: source.body.get(key) for key in
           ("origin", "coverage", "analysis", "execution_status")},
        "issues": source.body.get("issues", []),
        "segments": [s for s in source.body.get("segments", [])
                     if s["start"] < end and s["end"] > start],
    }


def delivered(result):
    """Only complete original-text windows, never score-only candidates."""
    if not isinstance(result, dict):
        return []
    candidates = result.get("windows", [result])
    return [w for w in candidates if isinstance(w, dict)
            and isinstance(w.get("ref"), str) and isinstance(w.get("text"), str)
            and type(w.get("offset")) is int and type(w.get("end")) is int
            and len(w["text"]) == w["end"] - w["offset"]]


def selection(store, study, value):
    try:
        ref, left, right = value.split(":")
        source = store.get(study, ref)
        if source.kind != "source":
            raise ValueError("expected source")
        result = window(source, int(left), int(right))
        if not result["text"].strip():
            raise ValueError("empty selection")
        return result
    except (TypeError, AttributeError, ValueError) as exc:
        raise ValueError("expected exact source_ref:start:end selection") from exc


def _line_offsets(text):
    offsets = [0, *(match.end() for match in re.finditer(r"\r\n|\r|\n", text))]
    if offsets[-1] < len(text):
        offsets.append(len(text))
    return offsets


def markdown_segments(text, origin, coverage):
    """Line maps retain exact source offsets, including tables and fenced code."""
    offsets = _line_offsets(text)
    labels = {"heading_open": "section_header", "table_open": "table",
              "list_item_open": "list_item", "fence": "code"}
    segments = []
    for token in MarkdownIt("commonmark").enable("table").parse(text):
        if token.type in labels and token.map:
            start, end = (offsets[i] for i in token.map)
            locator = {"url": origin, "label": labels[token.type]}
            if token.type == "heading_open":
                locator["level"] = int(token.tag[1:])
            segments.append({"start": start, "end": end, "locator": locator, "status": coverage})
    return segments or [{"start": 0, "end": len(text), "locator": {"url": origin}, "status": coverage}]


def chunks(source):
    text = source.body["text"]
    boundaries = {0, len(text)}
    structural = {0, len(text)}
    segments = sorted(source.body.get("segments", []), key=lambda row: row["start"])
    headings, lists = [], []
    last_page = None
    for segment in segments:
        boundaries.update(p for p in (segment["start"], segment["end"])
                          if 0 <= p <= len(text))
        locator = segment.get("locator", {})
        label, page = locator.get("label", ""), locator.get("page")
        if label in {"table", "code", "excerpt"}:
            structural.update((segment["start"], segment["end"]))
        if label in {"title", "section_header"}:
            # A nested heading chain belongs with its first content paragraph.
            nested = (headings and locator.get("level", 0) > headings[-1]["locator"].get("level", 0)
                      and not text[headings[-1]["end"]:segment["start"]].strip())
            if not nested:
                structural.add(segment["start"])
            headings.append(segment)
        if label == "list_item":
            if lists and not text[lists[-1][1]:segment["start"]].strip():
                lists[-1] = (lists[-1][0], max(lists[-1][1], segment["end"]))
            else:
                lists.append((segment["start"], segment["end"]))
        if page is not None and page != last_page:
            structural.add(segment["start"])
            last_page = page
    for start, end in lists:
        structural.update((start, end))
    boundaries.update(m.end() for m in re.finditer(r"\n[ \t]*\n", text))
    points = sorted(boundaries)
    ranges = []
    for start, end in zip(points, points[1:]):
        while end - start > CHUNK_CHARACTERS:
            stop = start + CHUNK_CHARACTERS
            in_table = any(seg["start"] <= start < seg["end"]
                           and seg.get("locator", {}).get("label") == "table" for seg in segments)
            choices = list(re.finditer(r"\n" if in_table else r"[。！？；.!?;]\s*|\n", text[start:stop]))
            if choices:
                stop = start + choices[-1].end()
            ranges.append((start, stop))
            start = stop
        if start < end:
            ranges.append((start, end))
    # Pack adjacent short paragraphs without losing any original characters.
    packed = []
    for start, end in ranges:
        if packed and start not in structural and end - packed[-1][0] <= CHUNK_CHARACTERS:
            packed[-1] = (packed[-1][0], end)
        else:
            packed.append((start, end))
    result = []
    for start, end in packed:
        content = text[start:end]
        for heading in reversed(headings):
            left, right = max(start, heading["start"]), min(end, heading["end"])
            if left < right:
                content = content[:left - start] + content[right - start:]
        if not content.strip():
            continue
        parents, context = [], []
        for segment in segments:
            locator = segment.get("locator", {})
            if segment["start"] > start:
                break
            if locator.get("label") in {"title", "section_header"}:
                level = locator.get("level", 0)
                while parents and parents[-1]["locator"].get("level", 0) >= level:
                    parents.pop()
                parents.append(segment)
            if locator.get("label") == "table" and segment["start"] < start < segment["end"]:
                lines = _line_offsets(text[segment["start"]:segment["end"]])
                header_end = segment["start"] + lines[min(2, len(lines) - 1)]
                context.append({"start": segment["start"], "end": min(header_end, start)})
        context.extend({"start": h["start"], "end": h["end"]} for h in parents if h["end"] <= start)
        result.append({"ref": source.ref, "start": start, "end": end, "context": context})
    return result


def terms(text):
    tokens = []
    for word in re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]+", text.casefold()):
        if '\u3400' <= word[0] <= '\u9fff':
            tokens.extend(word)
            tokens.extend(word[i:i + 2] for i in range(len(word) - 1))
        else:
            tokens.append(word)
    return tokens


def bm25(query, texts):
    """Okapi BM25 over this complete corpus, with positive Robertson IDF."""
    documents = [Counter(terms(text)) for text in texts]
    if not documents:
        return []
    lengths = [sum(doc.values()) for doc in documents]
    average = sum(lengths) / len(documents)
    frequencies = Counter(term for doc in documents for term in doc)
    wanted = set(terms(query))
    k1, b = 1.2, 0.75
    scores = []
    for doc, length in zip(documents, lengths):
        score = 0.0
        for term in wanted & doc.keys():
            df, tf = frequencies[term], doc[term]
            idf = log1p((len(documents) - df + 0.5) / (df + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / average))
        scores.append(score)
    return scores


def expanded_ranges(passages, scores, eligible=None):
    """Selected original passages plus headings/table headers, without overlap."""
    windows = {}
    if eligible is None:
        eligible = [score > 0 for score in scores]
    for item, score, keep in zip(passages, scores, eligible):
        if keep:
            windows.setdefault(item["ref"], []).extend(
                (part["start"], part["end"], score)
                for part in [*item.get("context", []), item]
            )
    ranges = ({"ref": ref, "start": start, "end": end, "score": score}
              for ref, rows in windows.items() for start, end, score in rows)
    selected, covered = [], {}
    for row in sorted(ranges, key=lambda r: -r["score"]):
        remaining = [(row["start"], row["end"])]
        for a, b in covered.get(row["ref"], []):
            remaining = [(left, right) for start, end in remaining
                         for left, right in ((start, min(end, a)), (max(start, b), end))
                         if left < right]
        for start, end in remaining:
            selected.append({**row, "start": start, "end": end})
            covered.setdefault(row["ref"], []).append((start, end))
    return selected
