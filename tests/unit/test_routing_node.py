# CMN-C1-171 — Unit Tests: RoutingNode (main)

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.routing_node import RoutingNode
from src.schemas.state import from_json


def _state(query, **extra):
    s = {"normalized_query": query, "validated_input": query,
         "node_history": [], "error_log": [], "execution_time": {}}
    s.update(extra)
    return s


class TestRoutingNode:
    def setup_method(self):
        self.node = RoutingNode()

    def test_routes_financial_request(self):
        result = self.node.execute(_state("I need to generate a financial disclosure report"))
        assert result["status"] == AgentStatus.SUCCESS
        # ADR-005: nested artifacts are stored as JSON strings — deserialize to assert.
        assert isinstance(result["routing_recommendation"], str)
        rec = from_json(result["routing_recommendation"], {})
        intent = from_json(result["intent"], {})
        assert rec["template_id"] == "SAMPLE-FIN-01"
        assert intent["industry"] == "FIN"
        assert result["catalog_kb_version"]

    def test_low_confidence_returns_top_candidates(self):
        """An ambiguous query yields candidates + a recommendation (top-N on low confidence)."""
        result = self.node.execute(_state("help me with something"))
        assert result["status"] == AgentStatus.SUCCESS
        rec = from_json(result["routing_recommendation"], {})
        assert "top_candidates" in rec

    def test_missing_query_error(self):
        result = self.node.execute(_state(""))
        assert result["status"] == AgentStatus.ERROR

    def test_missing_query_emits_trace_event(self, monkeypatch):
        """S-4: the reject path (missing normalized_query) must emit a domain event too."""
        calls = []
        monkeypatch.setattr(
            "src.nodes.routing_node.emit_trace_event",
            lambda event_type, payload, state: calls.append((event_type, payload)),
        )
        result = self.node.execute(_state(""))
        assert result["status"] == AgentStatus.ERROR
        assert calls, "expected emit_trace_event to be called on the reject path"
        assert calls[0][0] == "routing_reject"

    def test_insufficient_trust_rejected_via_call(self):
        # S-1: an insufficient caller must be rejected by the trust gate. This test calls
        # node(state), not .execute(state), so the real gate runs.
        state = _state("I need to generate a financial disclosure report", caller_trust_level=TrustLevel.ANONYMOUS.value)
        result = self.node(state)
        assert str(result["status"]).lower().endswith("error")
        assert any("trust gate denied" in msg.lower() for msg in result.get("error_log", []))

    def test_sufficient_trust_succeeds_via_call(self):
        state = _state("I need to generate a financial disclosure report", caller_trust_level=TrustLevel.VERIFIED_EXTERNAL.value)
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
