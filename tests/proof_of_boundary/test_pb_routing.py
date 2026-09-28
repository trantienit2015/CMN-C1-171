# Proof-of-Boundary: CMN-C1-171 routing invariants
#  PB-001  S-3 output gate rejects a non-catalog (injected) template_id.
#  PB-002  QueryNormalize enforces the 2000-char input cap (S-2).
#  PB-003  No keyword match still yields a valid, in-catalog recommendation
#          (deterministic fallback — never an empty/invalid route).

from framework.schemas.agent_status import AgentStatus
from src.nodes.query_normalize_node import MAX_QUERY_CHARS, QueryNormalizeNode
from src.nodes.response_validate_node import ResponseValidateNode
from src.nodes.routing_node import RoutingNode
from src.schemas.state import from_json, to_json


def _rv_state(rec, **extra):
    s = {
        "routing_recommendation": to_json(rec),
        "intent": to_json({"industry": "CMN", "pattern": "Chat", "confidence": 0.5}),
        "catalog_kb_version": "sample-catalog-v1",
        "node_history": [], "error_log": [], "execution_time": {},
    }
    s.update(extra)
    return s


class TestPBRouting:
    # PB-001 — S-3 membership gate is fail-closed on an injected template_id.
    def test_pb001_s3_rejects_injected_template_id(self):
        rec = {
            "template_id": "EVIL-C9-999",  # not a catalog member
            "confidence": 0.99, "rationale": "injected",
            "top_candidates": [{"template_id": "EVIL-C9-999"}],
        }
        result = ResponseValidateNode().execute(_rv_state(rec))
        assert result["status"] == AgentStatus.ERROR
        assert "S-3" in result["error_log"][0]
        # the invalid id must NOT leak into any output field
        assert "result" not in result and "formatted_output" not in result

    # PB-002 — input longer than the cap is truncated to MAX_QUERY_CHARS (S-2).
    def test_pb002_query_length_cap(self):
        long_q = "generate a financial report " * 200  # >> 2000 chars
        result = QueryNormalizeNode().execute({"user_input": long_q})
        assert result["status"] == AgentStatus.SUCCESS
        assert len(result["normalized_query"]) == MAX_QUERY_CHARS

    # PB-003 — a query with no keyword hit names no template.
    def test_pb003_no_match_names_no_template(self):
        """Nothing matched is an answer; naming a template anyway is not.

        The node used to fall back to the generic CMN entries at score 0, so an
        unmatched request came back carrying a specific id — indistinguishable,
        to the caller, from one the catalog actually supported.
        """
        result = RoutingNode().execute(
            {"normalized_query": "qwptzx nonsense zzz", "validated_input": "qwptzx nonsense zzz",
             "node_history": [], "error_log": [], "execution_time": {}}
        )
        assert result["status"] == AgentStatus.SUCCESS
        rec = from_json(result["routing_recommendation"], {})
        assert rec.get("template_id") is None
        assert not rec.get("top_candidates")
        assert rec["confidence"] == 0.0
