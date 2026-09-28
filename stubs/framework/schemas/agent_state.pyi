"""Type-only declaration of the framework's AgentState.

The installed framework carries annotations but ships no `py.typed` marker, so mypy
declines to read it and every symbol it exports arrives as `Any`. For a TypedDict base
that is not a mild loss of precision: a class inheriting `Any` stops being a TypedDict
as far as the checker is concerned, and `NotRequired` — the whole point of a state field
that a node may or may not write — becomes a syntax error in a position where it is
correct at runtime. Suppressing that per field hides a real contract instead of checking
it.

This file states the base's shape so the subclass in `src/schemas/state.py` is validated
as the TypedDict it actually is. It declares no behaviour and is never imported at
runtime; `mypy_path` in pyproject.toml points here. It mirrors
`framework.schemas.agent_state.AgentState` field for field, and comes out when the
distribution ships its own marker.
"""

from typing import Any, NotRequired, TypedDict

class AgentState(TypedDict):
    schema_version: str
    correlation_id: str
    trace_id: str
    session_id: str
    thread_id: str
    caller_trust_level: str
    caller_id: NotRequired[str]
    message_id: NotRequired[str | None]
    request_source: NotRequired[str | None]
    status: Any
    retry_count: int
    node_history: list[str]
    error_log: list[str]
    execution_time: dict[str, Any]
    user_input: str
    input_context: dict[str, Any]
    intent: str
    context: dict[str, Any]
    validated_input: Any
    enriched_context: dict[str, Any]
    messages: list[dict[str, Any]]
    result: Any
    llm_response: str
    iterations: int
    formatted_output: Any
    response_metadata: dict[str, Any]
    hitl_feedback: NotRequired[str | int | float | bool | list[Any] | dict[str, Any] | None]
    hitl_metadata: NotRequired[dict[str, Any]]
    hitl_status: NotRequired[Any]
    hitl_draft: NotRequired[str | int | float | bool | list[Any] | dict[str, Any] | None]
    hitl_count: NotRequired[int]
    hitl_allowed: NotRequired[bool]
    subgraph_thread_id: NotRequired[str | None]
