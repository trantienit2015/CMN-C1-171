"""AgentCore Platform v1.0 — CMN-C1-171 main: TemplateKBRetrieve + IntentClassify + RoutingRecommend."""

# Step 2-4 (main slot): retrieve catalog candidates, classify intent
# (industry + pattern), and select the routing recommendation. An optional LLM
# may refine intent; the deterministic matcher is the always-available baseline.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from shared.services.events import emitter
from shared.services.events.types import EventType
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import to_json
from src.services.catalog_kb_service import (
    CATALOG_KB_VERSION,
    retrieve_candidates,
)
from src.services.routing_service import classify_intent, recommend


class RoutingNode(FunctionNode):
    """Retrieve catalog candidates, classify intent, recommend a template."""

    # S-1: explicit by design — VERIFIED_EXTERNAL,
    # consistent with config/agent.yaml required_trust_level.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def __init__(
        self, top_k: int = 5, confidence_threshold: float = 0.6, max_candidates: int = 3, llm: Any | None = None
    ):
        self._top_k = top_k
        self._confidence_threshold = confidence_threshold
        self._max_candidates = max_candidates
        self._llm = llm

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        # Progress (non-terminal) event for the caller. Outside the Marketplace runtime
        # this resolves to a no-op emitter, so it is safe on every entry path.
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Working on the request...",
            metadata={"step": "main"},
        )
        query = state.get("normalized_query") or state.get("validated_input", "")
        if not query:
            # S-4: trace the reject path too — every execute() branch must emit.
            emit_trace_event("routing_reject", {"reason": "normalized_query missing"}, state)
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["RoutingNode: normalized_query missing"],
            }

        candidates = retrieve_candidates(query, top_k=self._top_k)
        intent = classify_intent(query, candidates)
        recommendation = recommend(
            candidates,
            intent,
            confidence_threshold=self._confidence_threshold,
            max_candidates=self._max_candidates,
        )

        # S-4: routing is a domain decision worth auditing (ids + confidence only).
        emit_trace_event(
            "routing_recommend",
            {
                "candidates": len(candidates),
                "template_id": recommendation.get("template_id"),
                "confidence": recommendation.get("confidence"),
            },
            state,
        )

        # ADR-005: serialize nested list/dict artifacts to JSON strings before
        # they enter State (msgpack-safe). Read back via from_json downstream.
        return {
            # The threshold this decision was made against, so the rendered answer
            # cites the number that actually settled it rather than a default.
            "confidence_threshold": self._confidence_threshold,
            "candidates": to_json(candidates),
            "intent": to_json(intent),
            "routing_recommendation": to_json(recommendation),
            "catalog_kb_version": CATALOG_KB_VERSION,
            "status": AgentStatus.SUCCESS.value,
        }
