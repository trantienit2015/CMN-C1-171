# CMN-C1-171 — Unit Tests: ResponseValidateNode (post_process + S-3 gate)

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.response_validate_node import ResponseValidateNode


def _state(rec, **extra):
    s = {"routing_recommendation": rec, "intent": {"industry": "FIN", "pattern": "DocGeneration", "confidence": 0.8},
         "catalog_kb_version": "sample-catalog-v1",
         "node_history": [], "error_log": [], "execution_time": {}}
    s.update(extra)
    return s


class TestResponseValidateNode:
    def setup_method(self):
        self.node = ResponseValidateNode()

    def test_valid_template_id_passes(self):
        rec = {"template_id": "SAMPLE-FIN-01", "confidence": 0.8, "rationale": "x",
               "top_candidates": [{"template_id": "SAMPLE-RAG-01"}]}
        result = self.node.execute(_state(rec))
        assert result["status"] == AgentStatus.SUCCESS
        assert result["result"]["template_id"] == "SAMPLE-FIN-01"

    def test_s3_rejects_unknown_template_id(self):
        """S-3: a template_id not in the catalog is rejected with ERROR."""
        rec = {"template_id": "ZZZ-C9-999", "confidence": 0.9, "rationale": "x", "top_candidates": []}
        result = self.node.execute(_state(rec))
        assert result["status"] == AgentStatus.ERROR
        assert "S-3" in result["error_log"][0]

    def test_s3_rejects_unknown_candidate(self):
        rec = {"template_id": "SAMPLE-FIN-01", "confidence": 0.8, "rationale": "x",
               "top_candidates": [{"template_id": "NOT-IN-CATALOG-00"}]}
        result = self.node.execute(_state(rec))
        assert result["status"] == AgentStatus.ERROR

    def test_insufficient_trust_rejected_via_call(self):
        # S-1: an insufficient caller must be rejected by the trust gate. This test calls
        # node(state), not .execute(state), so the real gate runs.
        rec = {"template_id": "SAMPLE-FIN-01", "confidence": 0.8, "rationale": "x",
               "top_candidates": [{"template_id": "SAMPLE-RAG-01"}]}
        state = _state(rec, caller_trust_level=TrustLevel.ANONYMOUS.value)
        result = self.node(state)
        assert str(result["status"]).lower().endswith("error")
        assert any("trust gate denied" in msg.lower() for msg in result.get("error_log", []))

    def test_sufficient_trust_succeeds_via_call(self):
        # S-1 clearance only — S-3 output re-check inspects the node's own result dict, not the
        # input state.
        rec = {"template_id": "SAMPLE-FIN-01", "confidence": 0.8, "rationale": "x",
               "top_candidates": [{"template_id": "SAMPLE-RAG-01"}]}
        state = _state(rec, caller_trust_level=TrustLevel.VERIFIED_EXTERNAL.value)
        result = self.node(state)
        assert not any("trust gate denied" in msg.lower() for msg in result.get("error_log", []))
