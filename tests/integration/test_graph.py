# CMN-C1-171 — Integration Test: full Cat 1 graph compile + invoke

from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from src.graph.graph import Graph


def _invoke(query: str):
    agent = Graph(config={"max_retry": 1, "top_k": 5})
    agent.compile()
    ctx = InvocationContext(
        session_id="it-session",
        caller_trust_level=TrustLevel.VERIFIED_EXTERNAL,
        caller_id="it-caller",
    )
    return agent.invoke(query, ctx=ctx)


class TestTemplateRoutingGraph:
    def test_routes_to_valid_template(self):
        result = _invoke("I need a healthcare clinical guideline Q&A agent")
        assert result["status"] in (AgentStatus.SUCCESS, AgentStatus.SUCCESS.value)
        out = result["output"]
        assert isinstance(out, str), "the caller reads this — it must not be a raw dict"
        assert "SAMPLE-HCR-01" in out
        assert "Catalog:" in out

    def test_ambiguous_query_does_not_crash(self):
        result = _invoke("do something useful")
        assert result["status"] in (AgentStatus.SUCCESS, AgentStatus.SUCCESS.value)

    def test_empty_input_does_not_crash(self):
        result = _invoke("   ")
        out = result.get("output")
        assert out in (None, {}) or out.get("template_id") in (None, "")

    def test_node_history_covers_backbone(self):
        result = _invoke("retail demand forecast question answering")
        joined = " ".join(result.get("node_history", []))
        assert "QueryNormalizeNode" in joined
        assert "RoutingNode" in joined
        assert "ResponseValidateNode" in joined
