# CMN-C1-171 — Unit Tests: QueryNormalizeNode (pre_process)

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.query_normalize_node import QueryNormalizeNode


class TestQueryNormalizeNode:
    def setup_method(self):
        self.node = QueryNormalizeNode()

    def test_success_normalizes(self):
        result = self.node.execute(
            {"user_input": "  I need a financial   report generator  ", "node_history": [], "error_log": []}
        )
        assert result["status"] == AgentStatus.SUCCESS
        assert result["normalized_query"] == "I need a financial report generator"
        assert result["validated_input"] == result["normalized_query"]

    def test_empty_input_error(self):
        result = self.node.execute({"user_input": "   ", "node_history": [], "error_log": []})
        assert result["status"] == AgentStatus.ERROR
        assert "empty" in result["error_log"][0].lower()

    def test_insufficient_trust_rejected_via_call(self):
        # S-1: an insufficient caller must be rejected by the trust gate. This test calls
        # node(state), not .execute(state), so the real gate runs.
        state = {"user_input": "I need a financial report generator", "node_history": [], "error_log": [], "caller_trust_level": TrustLevel.ANONYMOUS.value}
        result = self.node(state)
        assert str(result["status"]).lower().endswith("error")
        assert any("trust gate denied" in msg.lower() for msg in result.get("error_log", []))

    def test_sufficient_trust_succeeds_via_call(self):
        state = {"user_input": "I need a financial report generator", "node_history": [], "error_log": [], "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value}
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
