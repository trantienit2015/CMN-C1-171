"""AgentCore Platform v1.0 — CMN-C1-171 intent classification + routing scorer.

Deterministic-core logic for IntentClassify + RoutingRecommend. An optional LLM
may refine intent (injected via graph config); the deterministic path here is the
always-available baseline that tests exercise. No credentials, no external calls.
"""

from __future__ import annotations

from typing import Any

DEFAULT_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_MAX_CANDIDATES = 3

# Trigger hits on the top candidate for its evidence to count as complete. Below
# this the match rests on too little of the request to stand on its own.
FULL_EVIDENCE_HITS = 3


def _confidence(candidates: list[dict[str, Any]]) -> float:
    """How much the top candidate is worth believing.

    Two things decide it, and both are needed. **Evidence** is how much of the
    request the match actually rests on, so a single incidental word cannot carry
    a recommendation. **Separation** is how clearly the top candidate beats the
    runner-up, so a field of equally-plausible matches is reported as unresolved
    rather than settled by list order.

    Sharing out the total score was the earlier measure, and it read a lone
    one-word match as certainty: one candidate scoring 1 took the whole mass and
    came back at 1.0 — the strongest possible claim from the weakest possible
    evidence.
    """
    top = float(candidates[0].get("score", 0) or 0)
    if top <= 0:
        return 0.0
    runner_up = float(candidates[1].get("score", 0) or 0) if len(candidates) > 1 else 0.0
    evidence = min(1.0, top / FULL_EVIDENCE_HITS)
    separation = 1.0 if runner_up <= 0 else 0.5 + 0.5 * (top - runner_up) / top
    return round(evidence * separation, 3)


def classify_intent(query: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Infer {industry, pattern, confidence} from the top candidate.

    Deterministic: the highest-scored candidate's industry+pattern is the intent;
    confidence is `_confidence`'s reading of the candidate field.
    """
    if not candidates:
        return {"industry": "CMN", "pattern": "VectorRAG", "confidence": 0.0}
    top = candidates[0]
    confidence = _confidence(candidates)
    return {
        "industry": top["industry"],
        "pattern": top["pattern"],
        "confidence": confidence,
    }


def recommend(
    candidates: list[dict[str, Any]],
    intent: dict[str, Any],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> dict[str, Any]:
    """Select the best-match template_id; return top-N when below threshold.

    Returns {template_id, confidence, rationale, top_candidates[]}.
    """
    if not candidates:
        return {
            "template_id": None,
            "confidence": 0.0,
            "rationale": (
                "No catalog entry matched the request. Describe what the agent should do — "
                "the task, the data it works on, and the industry — rather than naming a product."
            ),
            "top_candidates": [],
        }

    top = candidates[0]
    confidence = intent.get("confidence", 0.0)
    top_n = [
        {
            "template_id": c["template_id"],
            "industry": c["industry"],
            "pattern": c["pattern"],
            "score": c.get("score", 0),
        }
        for c in candidates[:max_candidates]
    ]

    if confidence < confidence_threshold:
        rationale = (
            f"Confidence {confidence} below threshold {confidence_threshold}; "
            f"returning top {len(top_n)} candidates for human review."
        )
    else:
        rationale = (
            f"Best match {top['template_id']} ({top['industry']}/{top['pattern']}) " f"at confidence {confidence}."
        )

    return {
        "template_id": top["template_id"],
        "confidence": confidence,
        "rationale": rationale,
        "top_candidates": top_n,
    }
