"""Validated, opt-in document results from authorized external connectors."""

import hashlib
from datetime import datetime
from urllib.parse import parse_qsl, urlsplit


def obj(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


TEXT = {"type": "string", "minLength": 1}
SEGMENT = obj(
    {
        "start": {"type": "integer", "minimum": 0},
        "end": {"type": "integer", "minimum": 1},
        "locator": TEXT,
    }
)
DOCUMENT = obj(
    {
        "id": TEXT,
        "title": TEXT,
        "origin": TEXT,
        "retrieved_at": TEXT,
        "coverage": {"enum": ["metadata", "abstract", "partial_text", "fulltext"]},
        "text": TEXT,
        "segments": {"type": "array", "minItems": 1, "items": SEGMENT},
    }
)
LEAD = obj({"id": TEXT, "title": TEXT, "description": {"type": "string"}})
SCHEMA = {
    "oneOf": [
        obj(
            {
                "kind": {"const": "documents"},
                "documents": {"type": "array", "minItems": 1, "items": DOCUMENT},
            }
        ),
        obj(
            {
                "kind": {"const": "discovery"},
                "items": {"type": "array", "items": LEAD},
                "next_cursor": {"type": ["string", "null"]},
            }
        ),
        obj(
            {
                "kind": {"const": "status"},
                "status": {
                    "enum": [
                        "ready",
                        "login_required",
                        "verification_required",
                        "access_denied",
                        "rate_limited",
                        "unavailable",
                        "download_required",
                    ]
                },
                "message": TEXT,
            }
        ),
    ]
}


def decode(payload, server):
    """Validate the whole batch before persistence; never fetch returned URLs."""
    from jsonschema import Draft202012Validator

    if not Draft202012Validator(SCHEMA).is_valid(payload):
        raise ValueError("invalid knowledge-v1 result")
    if payload["kind"] != "documents":
        return dict(payload)
    sources, ids = [], set()
    for doc in payload["documents"]:
        if doc["id"] in ids:
            raise ValueError("duplicate document ID in result")
        ids.add(doc["id"])
        if not doc["text"].strip() or not doc["title"].strip():
            raise ValueError("document title and text must be nonempty")
        url = urlsplit(doc["origin"])
        forbidden = {
            "token",
            "access_token",
            "apikey",
            "api_key",
            "ticket",
            "signature",
            "cookie",
            "password",
            "authorization",
        }
        if (
            url.scheme not in {"https", "http"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.fragment
            or any(ord(c) < 33 for c in doc["origin"])
            or any(k.casefold() in forbidden for k, _ in parse_qsl(url.query))
        ):
            raise ValueError("document origin must be a public citation URL")
        try:
            stamp = datetime.fromisoformat(doc["retrieved_at"].replace("Z", "+00:00"))
            if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
                raise ValueError
        except (ValueError, OverflowError):
            raise ValueError("retrieved_at must be a UTC timestamp") from None
        previous = 0
        segments = []
        for segment in doc["segments"]:
            start, end = segment["start"], segment["end"]
            if (
                type(start) is not int
                or type(end) is not int
                or not previous <= start < end <= len(doc["text"])
                or not segment["locator"].strip()
            ):
                raise ValueError("invalid document segment offsets or locator")
            segments.append(
                {
                    **segment,
                    "locator": {"label": segment["locator"]},
                    "status": "connector_reported_not_reviewed",
                }
            )
            previous = end
        sources.append(
            {
                "origin": doc["origin"],
                "title": doc["title"],
                "text": doc["text"],
                "coverage": doc["coverage"],
                "segments": segments,
                "retrieved_at": doc["retrieved_at"],
                "document_id": doc["id"],
                "connector": server,
                "sha256": hashlib.sha256(doc["text"].encode("utf-8")).hexdigest(),
                "parser": "knowledge-v1",
                "issues": [],
                "coverage_basis": "connector_reported_not_reviewed",
            }
        )
    return {"sources": sources, "failures": []}
