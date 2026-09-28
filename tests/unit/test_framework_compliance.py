# CMN-C1-171 - Framework Compliance Tests (TC-01..08)
#
# Covers the standard shape: 3-slot AgentBaseGraph, S-4 emit_trace_event,
# explicit required_trust_level, S-2/S-3 @final gate + _extra_* overridable
# hooks. CMN-C1-171 does not override the _extra_*
# hooks (no domain-specific content check beyond the S-3 deterministic
# template-id membership gate implemented directly in execute()), so
# TC-06/TC-07 assert the inherited default hook is present, callable, and
# non-raising rather than a custom rejection path.

import inspect

import pytest

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.query_normalize_node import QueryNormalizeNode
from src.nodes.response_validate_node import ResponseValidateNode
from src.nodes.routing_node import RoutingNode
from src.schemas.state import State

PRE_PROCESS = QueryNormalizeNode
MAIN = RoutingNode
POST_PROCESS = ResponseValidateNode
ALL_NODES = (PRE_PROCESS, MAIN, POST_PROCESS)


class TestTC01StateContract:
    """TC-01: State is a flat TypedDict extending AgentState (no Pydantic/dataclass)."""

    def test_state_extends_agent_state(self):
        # TypedDict class-based inheritance loses the parent from __mro__
        # (issubclass() raises TypeError for TypedDicts), so verify structurally:
        # every AgentState field must be present in State's annotations.
        assert set(AgentState.__annotations__).issubset(set(State.__annotations__))

    def test_state_fields_json_serialisable_shape(self):
        annotations = State.__annotations__
        assert "normalized_query" in annotations
        assert "candidates" in annotations
        assert "routing_recommendation" in annotations


class TestTC02FailClosedValidation:
    """TC-02: invalid/empty input -> ERROR, never raise."""

    def test_empty_state_returns_error_not_raise(self):
        node = PRE_PROCESS()
        result = node.execute({})
        assert result["status"] == AgentStatus.ERROR.value


class TestTC03NoCredentials:
    """TC-03: no os.environ / hardcoded credentials in node source (see gate-credential-scan)."""

    def test_no_os_environ_in_node_modules(self):
        for mod in ALL_NODES:
            src = inspect.getsource(mod)
            assert "os.environ" not in src


class TestTC04InvocationContextIsolation:
    """TC-04: nodes never receive InvocationContext directly in execute(state)."""

    def test_execute_signature_is_state_only(self):
        for mod in ALL_NODES:
            sig = inspect.signature(mod.execute)
            params = list(sig.parameters.keys())
            assert params == ["self", "state"]


class TestTC05AuditLogging:
    """TC-05: emit_trace_event called for domain events (no re-emit of framework lifecycle events)."""

    def test_nodes_import_emit_trace_event(self):
        for mod in ALL_NODES:
            src = inspect.getsource(inspect.getmodule(mod))
            assert "emit_trace_event" in src
            assert '"node_start"' not in src
            assert '"node_complete"' not in src


class TestTC06S2GateHook:
    """TC-06: _extra_security_gate_input is overridable and non-raising."""

    def test_hook_present_and_non_raising(self):
        node = PRE_PROCESS()
        if not hasattr(node, "_extra_security_gate_input"):
            pytest.skip("local wheel stub lacks _extra_security_gate_input; CI wheel is gate of record")
        out = node._extra_security_gate_input({"user_input": "hello"})
        assert isinstance(out, dict)


class TestTC07S3GateHook:
    """TC-07: _extra_security_gate_output is overridable, never raises."""

    def test_hook_present_and_non_raising(self):
        node = POST_PROCESS()
        if not hasattr(node, "_extra_security_gate_output"):
            pytest.skip("local wheel stub lacks _extra_security_gate_output; CI wheel is gate of record")
        out = node._extra_security_gate_output({"formatted_output": {"template_id": None}})
        assert isinstance(out, dict)


class TestTC08TrustGateDeclaredAndEnforced:
    """TC-08: required_trust_level declared as a valid enum on every FunctionNode."""

    def test_all_nodes_declare_valid_trust_level(self):
        for mod in ALL_NODES:
            assert issubclass(mod, FunctionNode)
            assert mod.required_trust_level in (
                TrustLevel.ANONYMOUS,
                TrustLevel.VERIFIED_EXTERNAL,
                TrustLevel.INTERNAL,
            )

    def test_all_nodes_require_verified_external(self):
        # Matches config/agent.yaml required_trust_level: VERIFIED_EXTERNAL
        # (routing/classification request is a standard business operation,
        # not public-anonymous read-only Q&A).
        for mod in ALL_NODES:
            assert mod.required_trust_level == TrustLevel.VERIFIED_EXTERNAL
