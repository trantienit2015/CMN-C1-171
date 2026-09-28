"""AgentCore Platform v1.0 — CMN-C1-171 graph.

Enterprise Agent Skill Routing & Task Classification Agent.

Cat 1 — single technical capability (route an NL request to an AGENTIC STAR
template). Flat AgentBaseGraph backbone: QueryNormalize (pre_process) ->
retrieve+classify+recommend (main) -> generate+validate S-3 (post_process).
add_edges() is NOT overridden.
"""

from framework.graph.agent_base_graph import AgentBaseGraph

from src.nodes.query_normalize_node import QueryNormalizeNode
from src.nodes.response_validate_node import ResponseValidateNode
from src.nodes.routing_node import RoutingNode
from src.schemas.state import State


class TemplateRoutingGraph(AgentBaseGraph):
    """Routes a natural-language enterprise request to a template recommendation."""

    @property
    def name(self) -> str:
        return "cmn-c1-171"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects initialize + finalize
        top_k = self.config.get("top_k", 5) if hasattr(self, "config") else 5
        threshold = self.config.get("confidence_threshold", 0.6) if hasattr(self, "config") else 0.6
        max_c = self.config.get("max_routing_candidates", 3) if hasattr(self, "config") else 3
        llm = self.config.get("llm") if hasattr(self, "config") else None
        self._nodes["pre_process"] = QueryNormalizeNode()
        self._nodes["main"] = RoutingNode(top_k=top_k, confidence_threshold=threshold, max_candidates=max_c, llm=llm)
        self._nodes["post_process"] = ResponseValidateNode()

    # add_edges() not overridden — backbone wiring belongs to the framework.


# Stable alias for the standalone entry point import (src/api/server.py).
Graph = TemplateRoutingGraph
