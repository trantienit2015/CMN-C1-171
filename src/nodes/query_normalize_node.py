"""AgentCore Platform v1.0 — CMN-C1-171 pre_process: QueryNormalize."""

# Step 1: sanitize + truncate the natural-language routing request.
#  - S-1/S-2 input guard: reject empty input, collapse whitespace, cap length.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from shared.services.events import emitter
from shared.services.events.types import EventType
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

MAX_QUERY_CHARS = 2000


class QueryNormalizeNode(FunctionNode):
    """Normalize and sanitize the incoming routing request (pre_process)."""

    # S-1: explicit by design — VERIFIED_EXTERNAL,
    # consistent with config/agent.yaml required_trust_level.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        # Progress (non-terminal) event for the caller. Outside the Marketplace runtime
        # this resolves to a no-op emitter, so it is safe on every entry path.
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Checking the request...",
            metadata={"step": "pre_process"},
        )
        raw = state.get("user_input", "")

        # S-4: trace every invocation incl. the
        # reject path — counts only, no raw input / PII.
        emit_trace_event("query_normalize_received", {"input_length": len(raw or "")}, state)

        if not raw or not raw.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["QueryNormalizeNode: request is empty or missing"],
            }

        # Collapse whitespace + drop control chars and cap length (S-2).
        cleaned = " ".join(raw.split())[:MAX_QUERY_CHARS]

        return {
            "normalized_query": cleaned,
            "validated_input": cleaned,
            "status": AgentStatus.SUCCESS.value,
        }
