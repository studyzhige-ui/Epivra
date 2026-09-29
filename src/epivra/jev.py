"""Pinned TypeSafe decision contract. No internal retries or research mutations."""

import math

from .adapters import JsonAPI
from .domain import identity

MODEL = "jev-1.13.0"
ORIGIN = "https://api.typesafe.ai"
CREDENTIAL = "TYPESAFE_API_KEY"


class Jev:
    def __init__(self, api):
        self.api = api
        self.identity = identity("typesafe-decisions-v1", ORIGIN, MODEL)

    def payload(self, state, questions):
        payload = {"model": MODEL, "state": state, "questions": questions}
        # No documented local tokenizer: do not invent a character/token ratio.
        # Sources are chunked; oversized questions receive the provider's 422.
        return payload

    async def invoke(self, payload):
        return await self.api.post("/v1/systemone", payload)

    @staticmethod
    def retry_delay(raw, attempt):
        if raw.get("http_status") in {429, 529}:
            return raw.get("retry_after", 2 ** attempt)
        return None

    @staticmethod
    def decode(raw, questions):
        if raw.get("http_status") != 200:
            raise ValueError(f"TypeSafe request rejected: HTTP {raw.get('http_status')}")
        body = raw.get("data", {})
        if not isinstance(body, dict) or not isinstance(body.get("answers"), dict):
            raise ValueError("invalid TypeSafe response shape")
        answers = body.get("answers", {})
        if body.get("model") != MODEL or set(answers) != set(questions):
            raise ValueError("unexpected TypeSafe model or answer keys")
        for key, question in questions.items():
            answer = answers[key]
            if not isinstance(answer, dict) or answer.get("type") != question["type"]:
                raise ValueError("invalid TypeSafe answer type")
            probabilities = answer.get("probabilities", {})
            expected = set(question["criteria"]) if question["type"] == "choice" else {
                str(i) for i in range(len(question["criteria"]))}
            # Current observed wire responses round each probability to hundredths.
            # Account for aggregate rounding without renormalizing the receipt.
            if not isinstance(probabilities, dict) or set(probabilities) != expected or any(
                type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
                for p in probabilities.values()
            ) or not math.isclose(sum(probabilities.values()), 1, abs_tol=0.005 * len(expected) + 1e-9):
                raise ValueError("invalid TypeSafe probabilities")
            confidence = answer.get("confidence")
            if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("invalid TypeSafe confidence")
            if question["type"] == "choice":
                if not isinstance(answer.get("choice"), str) or answer["choice"] not in expected:
                    raise ValueError("invalid TypeSafe choice")
            else:
                score = answer.get("score")
                # Observed live responses round probabilities and scores independently to
                # two decimal places. Do not reconstruct its score from rounded
                # probabilities; retain the reported value and validate its range.
                if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= len(expected) - 1:
                    raise ValueError("invalid TypeSafe score")
        return answers


def connect(keys):
    key = keys.get(CREDENTIAL, "").strip()
    if not key:
        raise ValueError(f"{CREDENTIAL} required")
    return Jev(JsonAPI(ORIGIN, key, credential_env=CREDENTIAL))
