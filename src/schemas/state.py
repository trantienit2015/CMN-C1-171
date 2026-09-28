"""AgentCore Platform v1.0 — CMN-C1-171 state schema.

ADR-005: State must be a flat TypedDict — never Pydantic BaseModel. LangGraph
checkpoints use msgpack serialization; Pydantic objects and nested containers
(list[dict] / dict) are not msgpack-safe and cause silent corruption. Extend
AgentState with primitive fields only. Routing artifacts that are naturally
list/dict are stored JSON-serialized as Optional[str] and (de)serialized at the
node boundary via to_json / from_json. Do NOT add credentials, secrets, or
Pydantic models.
"""

from __future__ import annotations

import json
from typing import Any, NotRequired, Optional

from framework.schemas.agent_state import AgentState


def to_json(value: Any) -> Optional[str]:
    """Serialize a list/dict State value to a compact JSON string (ADR-005, msgpack-safe).

    Returns None for None so the field stays a true Optional[str].
    """
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def from_json(value: Any, default: Any) -> Any:
    """Deserialize a JSON-string State value back to its list/dict form.

    Tolerant by design: None/empty -> default; an already-native list/dict (e.g. a value
    supplied directly in a unit test) passes through unchanged; a malformed string -> default.
    """
    if value is None or value == "":
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


class State(AgentState):
    """Enterprise agent skill-routing / task-classification state.

    Shared fields (user_input, validated_input, status, session_id,
    node_history, error_log, result, formatted_output, ...) are inherited
    from AgentState — do NOT re-declare them.

    Every field below is optional at runtime: a node writes the ones it produces and
    the rest are simply absent, which is what NotRequired states. mypy cannot see that
    here — AgentState ships without a py.typed marker, so the base arrives as Any and
    this stops being a TypedDict as far as the checker is concerned, though it remains
    one at runtime. The per-field suppressions below say exactly that and nothing more;
    the framework's own AgentState carries the same kind of marker on its own fields.
    They come out when the base is readable.
    """

    # Step 1 — QueryNormalize (pre_process)
    normalized_query: NotRequired[str]
    # Threshold the routing decision was made against; the answer cites it.
    confidence_threshold: NotRequired[float]
    # Step 2 — TemplateKBRetrieve (main / service)
    # JSON list[{template_id, industry, pattern, description, score}]
    candidates: NotRequired[Optional[str]]

    # Step 3 — IntentClassify (main) writes the JSON {industry, pattern, confidence} into
    # the inherited `intent` field. It is not re-declared here: narrowing or widening a base
    # field changes the contract every other node reads.

    # Step 4 — RoutingRecommend (main)
    # JSON {template_id, confidence, rationale, top_candidates[]}
    routing_recommendation: NotRequired[Optional[str]]

    # KB coverage marker surfaced in output (stale-catalog awareness)
    catalog_kb_version: NotRequired[str]
