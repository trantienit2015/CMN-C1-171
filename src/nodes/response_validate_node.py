"""AgentCore Platform v1.0 — CMN-C1-171 post_process: ResponseGenerate + ResponseValidate (S-3)."""

# Step 5-6 (post_process): format the routing recommendation, then apply the
# S-3 deterministic output gate — every returned template_id (recommendation +
# top_candidates) MUST be a member of the catalog KB. On violation the
# output is dropped and ERROR is returned (no silent suppression, no auto-retry).

import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from shared.services.events import emitter
from shared.services.events.types import EventType
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import from_json
from src.services.catalog_kb_service import catalog_size, is_valid_template_id
from src.services.routing_service import DEFAULT_CONFIDENCE_THRESHOLD

_JA = re.compile(r"[぀-ヿ㐀-\u4dbf一-\u9fff]")


def _render(response: dict[str, Any], threshold: float, japanese: bool) -> str:
    """Turn the recommendation into something the caller can read and act on.

    The caller reads this. A dict rendered by `str()` puts the decision behind
    punctuation, and — worse — shows a template id next to a confidence of 0.0
    with equal weight, which reads as a recommendation whatever the number says.
    So the certainty decides the shape: a pick, a shortlist, or nothing found.
    """
    confidence = response.get("confidence", 0.0)
    candidates = response.get("top_candidates") or []
    version = response.get("catalog_kb_version") or ""

    if not response.get("template_id"):
        if japanese:
            return (
                "## 該当なし\n\n"
                f"カタログ {catalog_size()} 件のいずれにも当てはまりませんでした。\n"
                "エージェントに何をさせたいか（作業・扱うデータ・業種）を書くと絞り込めます。\n\n"
                f"カタログ: {version}"
            )
        return (
            "## No match\n\n"
            f"Nothing in the {catalog_size()}-entry catalog matched.\n"
            "Describe the task, the data it works on, and the industry to narrow it down.\n\n"
            f"Catalog: {version}"
        )

    def _where(c: dict[str, Any]) -> str:
        # A candidate carrying only an id still renders — a caller reading a
        # shortlist needs the ids more than the classification beside them.
        parts = [str(c[k]) for k in ("industry", "pattern") if c.get(k)]
        return f" ({' / '.join(parts)})" if parts else ""

    def _line(c: dict[str, Any]) -> str:
        return f"- **{c.get('template_id', '?')}**{_where(c)} — 一致 {c.get('score', 0)} 件"

    def _line_en(c: dict[str, Any]) -> str:
        return f"- **{c.get('template_id', '?')}**{_where(c)} — {c.get('score', 0)} trigger(s) matched"

    settled = confidence >= threshold
    if japanese:
        head = f"## 推奨: {response['template_id']}" if settled else "## 判断できませんでした — 候補を確認してください"
        body = [head, ""]
        if not settled:
            body += [
                f"確信度 {confidence}（判定に必要な {threshold} 未満）。" "以下は一致した候補で、推奨ではありません。",
                "",
            ]
        body += [_line(c) for c in candidates]
        body += ["", f"確信度: {confidence}", f"カタログ: {version}"]
        return "\n".join(body)

    head = f"## Recommended: {response['template_id']}" if settled else "## Not determined — review the candidates"
    body = [head, ""]
    if not settled:
        body += [
            f"Confidence {confidence} is below the {threshold} needed to settle on one. "
            "These matched; none is a recommendation.",
            "",
        ]
    body += [_line_en(c) for c in candidates]
    body += ["", f"Confidence: {confidence}", f"Catalog: {version}"]
    return "\n".join(body)


class ResponseValidateNode(FunctionNode):
    """Format the recommendation and S-3-validate template-ID membership."""

    # S-1: explicit by design — VERIFIED_EXTERNAL,
    # consistent with config/agent.yaml required_trust_level.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        # ADR-005: State stores these JSON-serialized; deserialize at the boundary.
        # Progress (non-terminal) event for the caller. Outside the Marketplace runtime
        # this resolves to a no-op emitter, so it is safe on every entry path.
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Preparing the result...",
            metadata={"step": "post_process"},
        )
        rec = from_json(state.get("routing_recommendation"), {})
        intent = from_json(state.get("intent"), {})

        # S-3 deterministic membership gate: collect every routed template_id.
        ids = []
        if rec.get("template_id"):
            ids.append(rec["template_id"])
        ids.extend(c.get("template_id") for c in rec.get("top_candidates", []))
        invalid = [tid for tid in ids if tid and not is_valid_template_id(tid)]

        if invalid:
            emit_trace_event("response_validate_reject", {"invalid_ids": invalid}, state)
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"ResponseValidateNode: S-3 gate rejected non-catalog template_id(s): {invalid}"],
            }

        response = {
            "template_id": rec.get("template_id"),
            "confidence": rec.get("confidence", 0.0),
            "rationale": rec.get("rationale", ""),
            "top_candidates": rec.get("top_candidates", []),
            "intent": intent,
            "catalog_kb_version": state.get("catalog_kb_version"),
        }

        emit_trace_event(
            "response_validate_pass",
            {"template_id": response["template_id"], "confidence": response["confidence"]},
            state,
        )

        threshold = float(state.get("confidence_threshold") or DEFAULT_CONFIDENCE_THRESHOLD)
        return {
            "result": response,
            "formatted_output": _render(response, threshold, bool(_JA.search(state.get("user_input", "")))),
            "status": AgentStatus.SUCCESS.value,
        }
